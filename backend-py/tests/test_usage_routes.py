from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.repository import AuthUser
from app.dependencies import get_current_user
from app.usage import routes


class FakeUsageService:
    def summarize_user(self, tenant_id, user_id, limit):
        return {"tenant_id": tenant_id, "user_id": user_id, "limit": limit, "records": []}


def test_my_usage_route_is_authenticated_and_scoped(monkeypatch):
    app = FastAPI()
    app.include_router(routes.router)
    client = TestClient(app)

    assert client.get("/api/usage/me").status_code == 401

    async def current_user():
        return AuthUser(
            id="user-1",
            tenant_id="tenant-1",
            email="usage@example.com",
            password_hash="unused",
        )

    app.dependency_overrides[get_current_user] = current_user
    monkeypatch.setattr(routes, "UsageService", FakeUsageService)

    response = client.get("/api/usage/me?limit=20")
    assert response.status_code == 200
    assert response.json() == {
        "tenant_id": "tenant-1",
        "user_id": "user-1",
        "limit": 20,
        "records": [],
    }
