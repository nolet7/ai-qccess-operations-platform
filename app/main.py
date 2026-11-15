from __future__ import annotations
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
import jwt
from jwt import PyJWKClient
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Numeric, DateTime, UniqueConstraint, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker
from sqlalchemy.exc import IntegrityError

class Base(DeclarativeBase):
    pass

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL required; never use ephemeral production storage")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

def get_db():
    with SessionLocal() as session:
        yield session

@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    scopes: frozenset[str]

bearer = HTTPBearer(auto_error=False)
def get_principal(auth: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    if auth is None:
        raise HTTPException(401, "Bearer token required")
    issuer = os.getenv("OIDC_ISSUER")
    audience = os.getenv("OIDC_AUDIENCE")
    jwks = os.getenv("OIDC_JWKS_URL")
    if not all([issuer, audience, jwks]):
        raise HTTPException(503, "OIDC issuer is not configured")
    try:
        key = PyJWKClient(jwks).get_signing_key_from_jwt(auth.credentials)
        claims = jwt.decode(auth.credentials, key.key, algorithms=["RS256"],
                            audience=audience, issuer=issuer,
                            options={"require":["sub","iss","aud","exp","iat"]})
    except Exception as error:
        raise HTTPException(401, "Invalid access token") from error
    tenant = claims.get("tenant_id")
    if not isinstance(tenant, str) or not tenant:
        raise HTTPException(403, "Tenant required")
    scopes = claims.get("scope", "")
    return Principal(claims["sub"], tenant, frozenset(scopes.split() if isinstance(scopes, str) else []))

def require(scope: str):
    def check(p: Principal = Depends(get_principal)):
        if scope not in p.scopes:
            raise HTTPException(403, "Insufficient scope")
        return p
    return check

app = FastAPI(version="0.1.0")
@app.get("/healthz")
def healthz():
    return {"status":"ok"}

@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status":"ready"}

class AccessRequest(Base):
    __tablename__="access_requests"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(100),index=True)
    requester: Mapped[str] = mapped_column(String(200))
    resource: Mapped[str] = mapped_column(String(200))
    permission: Mapped[str] = mapped_column(String(50))
    justification: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(30),default="pending")
    decided_by: Mapped[str | None] = mapped_column(String(200),nullable=True)

class AuditEvent(Base):
    __tablename__="audit_events"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(100),index=True)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(60))
    subject: Mapped[str] = mapped_column(String(36))

class AccessRequestNew(BaseModel):
    resource: str = Field(min_length=3,max_length=200)
    permission: str
    justification: str = Field(min_length=10,max_length=1000)

@app.post("/v1/access-requests",status_code=201)
def request_access(body:AccessRequestNew,p:Principal=Depends(require("access:request")),db:Session=Depends(get_db)):
    if body.permission not in {"viewer","editor","operator"}:raise HTTPException(422,"Permission not in policy")
    request=AccessRequest(tenant_id=p.tenant,requester=p.subject,**body.model_dump())
    db.add(request);db.flush()
    db.add(AuditEvent(tenant_id=p.tenant,actor=p.subject,action="requested",subject=request.id))
    db.commit();db.refresh(request)
    return {"id":request.id,"status":request.status}

@app.get("/v1/access-requests")
def requests(p:Principal=Depends(require("access:read")),db:Session=Depends(get_db)):
    return [{"id":r.id,"requester":r.requester,"resource":r.resource,"permission":r.permission,"status":r.status}
            for r in db.scalars(select(AccessRequest).where(AccessRequest.tenant_id==p.tenant))]

@app.post("/v1/access-requests/{request_id}/approve")
def approve(request_id:str,p:Principal=Depends(require("access:approve")),db:Session=Depends(get_db)):
    request=db.scalar(select(AccessRequest).where(AccessRequest.id==request_id,AccessRequest.tenant_id==p.tenant).with_for_update())
    if not request:raise HTTPException(404,"Request not found")
    if request.requester==p.subject:raise HTTPException(403,"No self approval")
    if request.status!="pending":raise HTTPException(409,"Already decided")
    request.status="approved";request.decided_by=p.subject
    db.add(AuditEvent(tenant_id=p.tenant,actor=p.subject,action="approved",subject=request.id))
    db.commit()
    return {"id":request.id,"status":request.status,"provisioned":False}

@app.get("/v1/audit")
def audit(p:Principal=Depends(require("access:audit")),db:Session=Depends(get_db)):
    return [{"actor":x.actor,"action":x.action,"subject":x.subject}
            for x in db.scalars(select(AuditEvent).where(AuditEvent.tenant_id==p.tenant))]

@app.get("/v1/access-requests/{request_id}/ai-advisory")
def advisory(request_id: str,p:Principal=Depends(require("access:analyze")),db:Session=Depends(get_db)):
    request=db.scalar(select(AccessRequest).where(AccessRequest.id==request_id,AccessRequest.tenant_id==p.tenant))
    if request is None:
        raise HTTPException(404,"Request not found")
    from app.ai import summarize_access
    note=summarize_access(request.resource,request.permission)
    return {"request_id":request.id,"advisory":note,"automated_decision":False}
