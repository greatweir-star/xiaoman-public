from fastapi import HTTPException

from app.auth.repository import InMemoryAuthRepository
from app.auth.service import AuthService
from app.config import Settings
from app.legacy_security import authorize_legacy_api_request, legacy_requested_user_id, resolve_ws_auth_user_id


def _service() -> AuthService:
    return AuthService(InMemoryAuthRepository(), Settings(jwt_secret="test-secret"))


def _register(service: AuthService):
    return service.register(email="kid@example.com", password="password123")


def test_legacy_path_extracts_owner():
    assert legacy_requested_user_id("/api/world/user-1/diary") == "user-1"
    assert legacy_requested_user_id("/api/memory/user-2") == "user-2"
    assert legacy_requested_user_id("/api/auth/login") is None


def test_required_legacy_api_auth_allows_owner_and_rejects_other_user():
    service = _service()
    pair = _register(service)
    settings = Settings(jwt_secret="test-secret", auth_required=True)
    header = f"Bearer {pair.access_token}"

    user = authorize_legacy_api_request(
        path=f"/api/world/{pair.user.id}/diary",
        authorization=header,
        service=service,
        settings=settings,
    )
    assert user and user.id == pair.user.id

    try:
        authorize_legacy_api_request(
            path="/api/world/someone-else/diary",
            authorization=header,
            service=service,
            settings=settings,
        )
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("cross-user request should fail")


def test_local_compatibility_mode_allows_legacy_request_without_token():
    assert authorize_legacy_api_request(
        path="/api/world/local-user/diary",
        authorization=None,
        settings=Settings(jwt_secret="test-secret", auth_required=False),
    ) is None


def test_websocket_auth_uses_access_token_and_rejects_spoofed_user_id():
    service = _service()
    pair = _register(service)
    settings = Settings(jwt_secret="test-secret", auth_required=True)

    assert resolve_ws_auth_user_id(
        {"accessToken": pair.access_token},
        service=service,
        settings=settings,
    ) == pair.user.id

    try:
        resolve_ws_auth_user_id(
            {"userId": "someone-else", "accessToken": pair.access_token},
            service=service,
            settings=settings,
        )
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("spoofed websocket user id should fail")


def test_websocket_auth_requires_token_when_enabled():
    try:
        resolve_ws_auth_user_id(
            {"userId": "local-user"},
            settings=Settings(jwt_secret="test-secret", auth_required=True),
        )
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("websocket token should be required")
