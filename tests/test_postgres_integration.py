from uuid import uuid4
import os
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.main import AccessRequest, AuditEvent

@pytest.mark.skipif(not os.getenv("DATABASE_URL","").startswith("postgresql"),reason="PostgreSQL-only integration test")
def test_postgresql_access_and_audit_transaction():
    engine=create_engine(os.environ["DATABASE_URL"])
    tenant="test-"+str(uuid4())
    with Session(engine) as db:
        r=AccessRequest(tenant_id=tenant,requester="employee",resource="synthetic-finance",
                        permission="viewer",justification="Synthetic corporate audit test",status="pending")
        db.add(r);db.flush()
        db.add(AuditEvent(tenant_id=tenant,actor="employee",action="requested",subject=r.id))
        db.commit()
        assert len(db.scalars(select(AuditEvent).where(AuditEvent.tenant_id==tenant)).all())==1
        assert db.scalar(select(AccessRequest).where(AccessRequest.tenant_id=="other")) is None
