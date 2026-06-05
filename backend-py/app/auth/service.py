"""Authentication service for the SaaS app shell."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.auth.models import AuthUserResponse, TokenPair
from app.auth.factory import build_auth_repository
from app.auth.passwords import hash_password, verify_password
from app.auth.repository import (
    DEFAULT_TENANT_ID,
    AuthRepository,
    AuthUser,
)
from app.auth.tokens import TokenError, create_token, decode_token, hash_token
from app.config import Settings, get_settings

ACCESS_TTL_SECONDS = 60 * 30
REFRESH_TTL_SECONDS = 60 * 60 * 24 * 30


def _token_secret(settings: Settings) -> str:
    if settings.jwt_secret:
        return settings.jwt_secret
    if settings.is_production:
        raise RuntimeError("JWT_SECRET must be set in production")
    return "xiaoman-dev-jwt-secret-change-me"


def _user_response(user: AuthUser) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        status=user.status,
    )


class AuthService:
    def __init__(self, repository: AuthRepository, settings: Settings | None = None) -> None:
        self.repository = repository
        self.settings = settings or get_settings()

    def register(self, *, email: str, password: str) -> TokenPair:
        if "@" not in email:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="email is invalid")
        password_hash = hash_password(password)
        try:
            user = self.repository.create_user(
                tenant_id=DEFAULT_TENANT_ID,
                email=email,
                password_hash=password_hash,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return self._issue_pair(user)

    def login(self, *, email: str, password: str) -> TokenPair:
        user = self.repository.get_user_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
        if user.status != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user is not active")
        return self._issue_pair(user)

    def refresh(self, refresh_token: str) -> TokenPair:
        payload = self.decode_refresh(refresh_token)
        refresh_hash = hash_token(refresh_token)
        session = self.repository.get_session_by_refresh_hash(refresh_hash)
        if not session or session.revoked_at is not None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh session revoked")
        if session.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh session expired")
        user = self.repository.get_user_by_id(str(payload["sub"]))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
        self.repository.revoke_session(refresh_hash)
        return self._issue_pair(user)

    def logout(self, refresh_token: str) -> None:
        self.repository.revoke_session(hash_token(refresh_token))

    def get_user_from_access_token(self, access_token: str) -> AuthUser:
        payload = self.decode_access(access_token)
        user = self.repository.get_user_by_id(str(payload["sub"]))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
        if user.status != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user is not active")
        return user

    def decode_access(self, token: str) -> dict:
        try:
            return decode_token(token, secret=_token_secret(self.settings), expected_type="access")
        except TokenError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    def decode_refresh(self, token: str) -> dict:
        try:
            return decode_token(token, secret=_token_secret(self.settings), expected_type="refresh")
        except TokenError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    def _issue_pair(self, user: AuthUser) -> TokenPair:
        secret = _token_secret(self.settings)
        access_token = create_token(
            secret=secret,
            subject=user.id,
            tenant_id=user.tenant_id,
            token_type="access",
            expires_in=ACCESS_TTL_SECONDS,
            roles=("user",),
        )
        refresh_token = create_token(
            secret=secret,
            subject=user.id,
            tenant_id=user.tenant_id,
            token_type="refresh",
            expires_in=REFRESH_TTL_SECONDS,
            roles=("user",),
        )
        self.repository.create_session(
            tenant_id=user.tenant_id,
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_token),
            ttl_seconds=REFRESH_TTL_SECONDS,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TTL_SECONDS,
            user=_user_response(user),
        )


_repo = build_auth_repository()
_service = AuthService(_repo)


def get_auth_service() -> AuthService:
    return _service
