"""PostgreSQL auth repository regression tests."""

from datetime import datetime, timezone

import pytest

from app.auth.factory import build_auth_repository
from app.auth.postgres_repository import PostgresAuthRepository
from app.auth.repository import InMemoryAuthRepository
from app.config import Settings


class ScriptedCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query, params=()):
        self.connection.queries.append((" ".join(query.split()), params))

    def fetchone(self):
        return self.connection.fetchone_results.pop(0) if self.connection.fetchone_results else None


class ScriptedConnection:
    def __init__(self):
        self.queries = []
        self.fetchone_results = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def cursor(self):
        return ScriptedCursor(self)


def test_auth_repository_factory_keeps_file_mode_in_memory():
    repository = build_auth_repository(Settings(storage_backend="file"))
    assert isinstance(repository, InMemoryAuthRepository)


def test_auth_repository_factory_requires_postgres_url():
    with pytest.raises(RuntimeError):
        build_auth_repository(Settings(storage_backend="postgres", database_url=""))


def test_postgres_auth_repository_executes_parameterized_crud():
    connection = ScriptedConnection()
    repository = PostgresAuthRepository("postgresql://xiaoman:test@localhost/xiaoman", lambda _: connection)

    user = repository.create_user(tenant_id="default", email="Kid@Example.com", password_hash="hash")
    assert user.email == "kid@example.com"

    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    connection.fetchone_results.append((user.id, "default", user.email, "hash", "active", now))
    assert repository.get_user_by_email("KID@example.com") == user.__class__(
        id=user.id,
        tenant_id="default",
        email="kid@example.com",
        password_hash="hash",
        status="active",
        created_at=now,
    )

    session = repository.create_session(
        tenant_id="default",
        user_id=user.id,
        refresh_token_hash="refresh-hash",
        ttl_seconds=3600,
    )
    connection.fetchone_results.append((
        session.id,
        "default",
        user.id,
        "refresh-hash",
        session.expires_at,
        None,
    ))
    assert repository.get_session_by_refresh_hash("refresh-hash") == session
    repository.revoke_session("refresh-hash")

    queries = "\n".join(query for query, _ in connection.queries)
    assert "INSERT INTO tenants" in queries
    assert "INSERT INTO users" in queries
    assert "INSERT INTO auth_sessions" in queries
    assert "UPDATE auth_sessions" in queries
