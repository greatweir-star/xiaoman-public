import json
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.repository import InMemoryAuthRepository
from app.auth.service import AuthService, get_auth_service
from app.config import Settings
from app.guest_claims.migration import FileGuestMigrator
from app.guest_claims.repository import FileGuestClaimRepository
from app.guest_claims.routes import router
from app.guest_claims.service import GuestClaimService, get_guest_claim_service


def test_guest_claim_routes_require_login_and_migrate_data(tmp_path):
    guest_id = str(uuid.uuid4())
    identity_path = tmp_path / "users" / guest_id / "user" / "identity.json"
    identity_path.parent.mkdir(parents=True)
    identity_path.write_text(json.dumps({"name": "Guest"}), encoding="utf-8")

    settings = Settings(jwt_secret="route-guest-claim-secret")
    auth_service = AuthService(InMemoryAuthRepository(), settings)
    claim_service = GuestClaimService(
        FileGuestClaimRepository(str(tmp_path)),
        FileGuestMigrator(str(tmp_path)),
        settings,
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_guest_claim_service] = lambda: claim_service
    client = TestClient(app)

    pair = auth_service.register(email="route-claim@example.com", password="password123")
    issued = client.post("/api/auth/guest-claim-token", json={"guest_id": guest_id})
    assert issued.status_code == 200

    unauthorized = client.post(
        "/api/auth/claim-guest",
        json={"guest_id": guest_id, "claim_token": issued.json()["claim_token"]},
    )
    assert unauthorized.status_code == 401

    claimed = client.post(
        "/api/auth/claim-guest",
        headers={"Authorization": f"Bearer {pair.access_token}"},
        json={"guest_id": guest_id, "claim_token": issued.json()["claim_token"]},
    )
    assert claimed.status_code == 200
    assert claimed.json()["status"] == "completed"
    assert (tmp_path / "users" / pair.user.id / "user" / "identity.json").exists()
