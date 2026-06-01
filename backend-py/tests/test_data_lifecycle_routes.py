from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.repository import AuthUser
from app.data_lifecycle.routes import get_data_lifecycle_service, router
from app.data_lifecycle.service import DataLifecycleService
from app.dependencies import get_current_user
from app.operations.service import get_audit_service
from app.config import Settings


class RecordingAudit:
    def __init__(self):
        self.actions = []

    def record(self, **event):
        self.actions.append(event["action"])


def test_data_lifecycle_routes_require_auth_and_confirmation(tmp_path):
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert client.post("/api/account/export").status_code == 401

    async def current_user():
        return AuthUser(id="user-1", tenant_id="tenant-1", email="data@example.com", password_hash="unused")

    identity = tmp_path / "users" / "user-1" / "user" / "identity.json"
    identity.parent.mkdir(parents=True)
    identity.write_text("{}", encoding="utf-8")
    audit = RecordingAudit()
    service = DataLifecycleService(Settings(storage_backend="file"), data_dir=str(tmp_path))
    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_data_lifecycle_service] = lambda: service
    app.dependency_overrides[get_audit_service] = lambda: audit

    exported = client.post("/api/account/export")
    assert exported.status_code == 200
    assert client.get(exported.json()["download_url"]).status_code == 200
    assert client.post("/api/account/delete-data", json={"confirmation": "wrong"}).status_code == 422
    deleted = client.post("/api/account/delete-data", json={"confirmation": "DELETE"})
    assert deleted.status_code == 200
    assert audit.actions == ["data.export", "data.delete.requested", "data.delete.completed"]
