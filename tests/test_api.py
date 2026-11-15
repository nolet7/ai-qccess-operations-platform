import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import main as m

@pytest.fixture
def lab():
    engine=create_engine("sqlite+pysqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    m.Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine)
    principals={}
    def get_db():
        with factory() as s: yield s
    def get_principal(req:Request):
        token=req.headers.get("Authorization","").removeprefix("Bearer ")
        if token not in principals:raise HTTPException(401,"Unauthorized")
        return principals[token]
    m.app.dependency_overrides[m.get_db]=get_db
    m.app.dependency_overrides[m.get_principal]=get_principal
    with TestClient(m.app) as client:
        def auth(user,tenant,scopes):
            token="test-"+str(len(principals))
            principals[token]=m.Principal(user,tenant,frozenset(scopes))
            return {"Authorization":"Bearer "+token}
        yield client,auth
    m.app.dependency_overrides.clear()
    engine.dispose()

def test_health(lab):
    client,auth=lab
    assert client.get("/healthz").json()=={"status":"ok"}

def test_bearer_is_required():
    with pytest.raises(HTTPException) as e:
        m.get_principal(None)
    assert e.value.status_code==401

def test_separation_of_duties_and_audit(lab):
    client,auth=lab
    employee=auth("employee","tenant-a",["access:request","access:approve"])
    manager=auth("manager","tenant-a",["access:approve","access:audit"])
    req=client.post("/v1/access-requests",headers=employee,json={"resource":"finance-reports","permission":"viewer","justification":"Monthly financial close"})
    assert req.status_code==201,req.text
    path="/v1/access-requests/"+req.json()["id"]+"/approve"
    assert client.post(path,headers=employee).status_code==403
    result=client.post(path,headers=manager)
    assert result.status_code==200 and result.json()["provisioned"] is False
    assert client.post(path,headers=manager).status_code==409
    assert len(client.get("/v1/audit",headers=manager).json())==2

def test_invalid_permission(lab):
    client,auth=lab
    employee=auth("employee","tenant-a",["access:request"])
    assert client.post("/v1/access-requests",headers=employee,json={"resource":"finance-reports","permission":"owner","justification":"I need access to reports"}).status_code==422
