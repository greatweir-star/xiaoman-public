from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.repository import InMemoryAuthRepository
from app.auth.routes import router
from app.auth.service import AuthService, get_auth_service
from app.config import Settings
from app.operations.service import get_audit_service


class RecordingAudit:
    def __init__(self):
        self.actions = []

    def record(self, **event):
        self.actions.append(event)


def test_auth_routes_emit_audit_events():
    app = FastAPI()
    app.include_router(router)
    service = AuthService(InMemoryAuthRepository(), Settings(jwt_secret="audit-route-secret"))
    audit = RecordingAudit()
    app.dependency_overrides[get_auth_service] = lambda: service
    app.dependency_overrides[get_audit_service] = lambda: audit
    client = TestClient(app)

    registered = client.post("/api/auth/register", json={"email": "audit@example.com", "password": "password123"})
    logged_in = client.post("/api/auth/login", json={"email": "audit@example.com", "password": "password123"})
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": logged_in.json()["refresh_token"]})
    logged_out = client.post("/api/auth/logout", json={"refresh_token": refreshed.json()["refresh_token"]})

    assert registered.status_code == 201
    assert logged_out.status_code == 204
    assert [event["action"] for event in audit.actions] == [
        "auth.register",
        "auth.login",
        "auth.refresh",
        "auth.logout",
    ]
