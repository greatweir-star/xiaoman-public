"""Select the configured auth repository."""

from __future__ import annotations

from typing import Any, Callable

from app.auth.postgres_repository import PostgresAuthRepository
from app.auth.repository import AuthRepository, InMemoryAuthRepository
from app.config import Settings, get_settings


def build_auth_repository(
    settings: Settings | None = None,
    *,
    postgres_connect: Callable[[str], Any] | None = None,
) -> AuthRepository:
    settings = settings or get_settings()
    if settings.uses_postgres:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is required for PostgreSQL auth persistence")
        return PostgresAuthRepository(settings.database_url, postgres_connect)
    return InMemoryAuthRepository()
