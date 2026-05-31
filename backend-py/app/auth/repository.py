"""Auth repository interfaces and an in-memory development implementation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol


DEFAULT_TENANT_ID = "default"


@dataclass
class AuthUser:
    id: str
    tenant_id: str
    email: str
    password_hash: str
    status: str = "active"
    created_at: datetime | None = None


@dataclass
class AuthSession:
    id: str
    tenant_id: str
    user_id: str
    refresh_token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None


class AuthRepository(Protocol):
    def get_user_by_email(self, email: str) -> AuthUser | None:
        ...

    def get_user_by_id(self, user_id: str) -> AuthUser | None:
        ...

    def create_user(self, *, tenant_id: str, email: str, password_hash: str) -> AuthUser:
        ...

    def create_session(
        self,
        *,
        tenant_id: str,
        user_id: str,
        refresh_token_hash: str,
        ttl_seconds: int,
    ) -> AuthSession:
        ...

    def get_session_by_refresh_hash(self, refresh_token_hash: str) -> AuthSession | None:
        ...

    def revoke_session(self, refresh_token_hash: str) -> None:
        ...


class InMemoryAuthRepository:
    """Small development repository used by the SaaS app shell and tests."""

    def __init__(self) -> None:
        self._users_by_id: dict[str, AuthUser] = {}
        self._users_by_email: dict[str, AuthUser] = {}
        self._sessions_by_refresh_hash: dict[str, AuthSession] = {}

    def get_user_by_email(self, email: str) -> AuthUser | None:
        return self._users_by_email.get(email.strip().lower())

    def get_user_by_id(self, user_id: str) -> AuthUser | None:
        return self._users_by_id.get(user_id)

    def create_user(self, *, tenant_id: str, email: str, password_hash: str) -> AuthUser:
        normalized = email.strip().lower()
        if normalized in self._users_by_email:
            raise ValueError("email already registered")
        user = AuthUser(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            email=normalized,
            password_hash=password_hash,
            created_at=datetime.now(timezone.utc),
        )
        self._users_by_id[user.id] = user
        self._users_by_email[user.email] = user
        return user

    def create_session(
        self,
        *,
        tenant_id: str,
        user_id: str,
        refresh_token_hash: str,
        ttl_seconds: int,
    ) -> AuthSession:
        session = AuthSession(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        )
        self._sessions_by_refresh_hash[refresh_token_hash] = session
        return session

    def get_session_by_refresh_hash(self, refresh_token_hash: str) -> AuthSession | None:
        return self._sessions_by_refresh_hash.get(refresh_token_hash)

    def revoke_session(self, refresh_token_hash: str) -> None:
        session = self._sessions_by_refresh_hash.get(refresh_token_hash)
        if session:
            session.revoked_at = datetime.now(timezone.utc)

