import asyncio

from fastapi import HTTPException

from app.auth.routes import auth_health
from app.auth.service import AuthService
from app.auth.repository import InMemoryAuthRepository
from app.auth.tokens import TokenError, decode_token
from app.config import Settings


def _service() -> AuthService:
    settings = Settings(jwt_secret="test-secret")
    return AuthService(InMemoryAuthRepository(), settings)


def test_register_login_and_access_token_roundtrip():
    service = _service()
    pair = service.register(email="kid@example.com", password="password123")

    assert pair.user.email == "kid@example.com"
    current = service.get_user_from_access_token(pair.access_token)
    assert current.id == pair.user.id

    login_pair = service.login(email="kid@example.com", password="password123")
    assert login_pair.user.id == pair.user.id


def test_invalid_password_is_rejected():
    service = _service()
    service.register(email="kid@example.com", password="password123")

    try:
        service.login(email="kid@example.com", password="wrong")
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("invalid password should fail")


def test_refresh_and_logout():
    service = _service()
    pair = service.register(email="kid@example.com", password="password123")

    refreshed = service.refresh(pair.refresh_token)
    assert refreshed.user.id == pair.user.id
    try:
        service.refresh(pair.refresh_token)
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("rotated refresh token should be revoked")

    service.logout(refreshed.refresh_token)
    try:
        service.refresh(refreshed.refresh_token)
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("revoked refresh token should fail")


def test_token_signature_is_checked():
    service = _service()
    pair = service.register(email="kid@example.com", password="password123")

    try:
        decode_token(pair.access_token, secret="other-secret", expected_type="access")
    except TokenError:
        pass
    else:
        raise AssertionError("token signed with a different secret should fail")


def test_auth_health_exposes_required_mode():
    result = asyncio.run(auth_health(Settings(auth_required=True)))
    assert result == {"status": "ok", "auth_required": True}
