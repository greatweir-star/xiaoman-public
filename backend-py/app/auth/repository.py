"""Auth repository interfaces with local-memory and PostgreSQL implementations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from psycopg import connect
from psycopg.rows import dict_row

from app.config import Settings, get_settings


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


class PostgresAuthRepository:
    """Persist SaaS accounts and refresh sessions in PostgreSQL."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self):
        return connect(self.database_url, row_factory=dict_row)

    @staticmethod
    def _user(row) -> AuthUser | None:
        return AuthUser(**row) if row else None

    @staticmethod
    def _session(row) -> AuthSession | None:
        return AuthSession(**row) if row else None

    def get_user_by_email(self, email: str) -> AuthUser | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, tenant_id, email, password_hash, status, created_at FROM users WHERE email = %s",
                (email.strip().lower(),),
            )
            return self._user(cursor.fetchone())

    def get_user_by_id(self, user_id: str) -> AuthUser | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, tenant_id, email, password_hash, status, created_at FROM users WHERE id = %s",
                (user_id,),
            )
            return self._user(cursor.fetchone())

    def create_user(self, *, tenant_id: str, email: str, password_hash: str) -> AuthUser:
        normalized = email.strip().lower()
        user_id = str(uuid.uuid4())
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tenants (id, name)
                VALUES (%s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (tenant_id, tenant_id),
            )
            try:
                cursor.execute(
                    """
                    INSERT INTO users (id, tenant_id, email, password_hash)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, tenant_id, email, password_hash, status, created_at
                    """,
                    (user_id, tenant_id, normalized, password_hash),
                )
            except Exception as exc:
                if getattr(exc, "sqlstate", "") == "23505":
                    raise ValueError("email already registered") from exc
                raise
            return self._user(cursor.fetchone())  # type: ignore[return-value]

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
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO auth_sessions (id, tenant_id, user_id, refresh_token_hash, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (session.id, session.tenant_id, session.user_id, session.refresh_token_hash, session.expires_at),
            )
        return session

    def get_session_by_refresh_hash(self, refresh_token_hash: str) -> AuthSession | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, tenant_id, user_id, refresh_token_hash, expires_at, revoked_at
                FROM auth_sessions
                WHERE refresh_token_hash = %s
                """,
                (refresh_token_hash,),
            )
            return self._session(cursor.fetchone())

    def revoke_session(self, refresh_token_hash: str) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE auth_sessions SET revoked_at = now() WHERE refresh_token_hash = %s",
                (refresh_token_hash,),
            )


def create_auth_repository(settings: Settings | None = None) -> AuthRepository:
    runtime_settings = settings or get_settings()
    if runtime_settings.uses_postgres:
        if not runtime_settings.database_url:
            raise RuntimeError("DATABASE_URL is required when XIAOMAN_STORAGE_BACKEND=postgres")
        return PostgresAuthRepository(runtime_settings.database_url)
    return InMemoryAuthRepository()
