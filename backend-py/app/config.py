"""Runtime configuration for the V0.03 SaaS application shell."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _csv_env(name: str, default: str = "") -> tuple[str, ...]:
    value = os.environ.get(name, default)
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Environment-backed settings shared by SaaS modules."""

    env: str = os.environ.get("XIAOMAN_ENV", "local")
    storage_backend: str = os.environ.get("XIAOMAN_STORAGE_BACKEND", "file")
    queue_backend: str = os.environ.get("XIAOMAN_QUEUE_BACKEND", "inline")
    database_url: str = os.environ.get("DATABASE_URL", "")
    redis_url: str = os.environ.get("REDIS_URL", "")
    jwt_secret: str = os.environ.get("JWT_SECRET", "")
    auth_required: bool = _bool_env("XIAOMAN_AUTH_REQUIRED")
    cors_allowed_origins: tuple[str, ...] = _csv_env(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
    )

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def uses_postgres(self) -> bool:
        return self.storage_backend.lower() == "postgres"

    @property
    def uses_queue(self) -> bool:
        return self.queue_backend.lower() != "inline"

    @property
    def requires_auth(self) -> bool:
        return self.auth_required or self.is_production


def get_settings() -> Settings:
    return Settings()
