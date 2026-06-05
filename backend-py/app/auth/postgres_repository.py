"""PostgreSQL persistence for SaaS authentication."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app.auth.repository import AuthSession, AuthUser, DEFAULT_TENANT_ID

ConnectionFactory = Callable[[str], Any]


def _default_connect(database_url: str) -> Any:
    try:
        import psycopg
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "psycopg is required for PostgreSQL auth persistence; install backend-py requirements"
        ) from exc
    return psycopg.connect(database_url)


def _auth_user(row: tuple[Any, ...] | None) -> AuthUser | None:
    if not row:
        return None
    return AuthUser(
        id=str(row[0]),
        tenant_id=str(row[1]),
        email=str(row[2]),
        password_hash=str(row[3]),
        status=str(row[4]),
        created_at=row[5],
    )


def _auth_session(row: tuple[Any, ...] | None) -> AuthSession | None:
    if not row:
        return None
    return AuthSession(
        id=str(row[0]),
        tenant_id=str(row[1]),
        user_id=str(row[2]),
        refresh_token_hash=str(row[3]),
        expires_at=row[4],
        revoked_at=row[5],
    )


class PostgresAuthRepository:
    def __init__(self, database_url: str, connect: ConnectionFactory | None = None) -> None:
        self.database_url = database_url
        self.connect = connect or _default_connect

    def _connection(self) -> Any:
        return self.connect(self.database_url)

    def get_user_by_email(self, email: str) -> AuthUser | None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, tenant_id, email, password_hash, status, created_at
                FROM users
                WHERE email = %s
                """,
                (email.strip().lower(),),
            )
            return _auth_user(cursor.fetchone())

    def get_user_by_id(self, user_id: str) -> AuthUser | None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, tenant_id, email, password_hash, status, created_at
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            return _auth_user(cursor.fetchone())

    def create_user(self, *, tenant_id: str, email: str, password_hash: str) -> AuthUser:
        normalized_email = email.strip().lower()
        user = AuthUser(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            email=normalized_email,
            password_hash=password_hash,
            created_at=datetime.now(timezone.utc),
        )
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tenants (id, name)
                VALUES (%s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (tenant_id, "Default"),
            )
            try:
                cursor.execute(
                    """
                    INSERT INTO users (id, tenant_id, email, password_hash, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user.id, user.tenant_id, user.email, user.password_hash, user.status, user.created_at),
                )
            except Exception as exc:
                if getattr(exc, "sqlstate", "") == "23505":
                    raise ValueError("email already registered") from exc
                raise
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
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO auth_sessions (id, tenant_id, user_id, refresh_token_hash, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (session.id, session.tenant_id, session.user_id, session.refresh_token_hash, session.expires_at),
            )
        return session

    def get_session_by_refresh_hash(self, refresh_token_hash: str) -> AuthSession | None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, tenant_id, user_id, refresh_token_hash, expires_at, revoked_at
                FROM auth_sessions
                WHERE refresh_token_hash = %s
                """,
                (refresh_token_hash,),
            )
            return _auth_session(cursor.fetchone())

    def revoke_session(self, refresh_token_hash: str) -> None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE auth_sessions
                SET revoked_at = now()
                WHERE refresh_token_hash = %s AND revoked_at IS NULL
                """,
                (refresh_token_hash,),
            )


__all__ = ["DEFAULT_TENANT_ID", "PostgresAuthRepository"]
