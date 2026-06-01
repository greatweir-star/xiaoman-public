from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.routes import router


def test_auth_route_roundtrip_including_logout():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    email = "route-smoke@example.com"

    registered = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert registered.status_code == 201

    logged_in = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert logged_in.status_code == 200

    refreshed = client.post(
        "/api/auth/refresh",
        json={"refresh_token": logged_in.json()["refresh_token"]},
    )
    assert refreshed.status_code == 200

    logged_out = client.post(
        "/api/auth/logout",
        json={"refresh_token": refreshed.json()["refresh_token"]},
    )
    assert logged_out.status_code == 204
    assert logged_out.content == b""
