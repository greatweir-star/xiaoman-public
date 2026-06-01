"""Runtime configuration for the V0.03 SaaS application shell."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _csv_env(name: str, default: str = "") -> tuple[str, ...]:
    value = os.environ.get(name, default)
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def _float_env(name: str, default: float) -> float:
    return float(os.environ.get(name, str(default)))


@dataclass(frozen=True)
class Settings:
    """Environment-backed settings shared by SaaS modules."""

    env: str = field(default_factory=lambda: os.environ.get("XIAOMAN_ENV", "local"))
    storage_backend: str = field(default_factory=lambda: os.environ.get("XIAOMAN_STORAGE_BACKEND", "file"))
    queue_backend: str = field(default_factory=lambda: os.environ.get("XIAOMAN_QUEUE_BACKEND", "inline"))
    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", ""))
    redis_url: str = field(default_factory=lambda: os.environ.get("REDIS_URL", ""))
    jwt_secret: str = field(default_factory=lambda: os.environ.get("JWT_SECRET", ""))
    auth_required: bool = field(default_factory=lambda: _bool_env("XIAOMAN_AUTH_REQUIRED"))
    rate_limit_messages: int = field(default_factory=lambda: _int_env("XIAOMAN_RATE_LIMIT_MESSAGES", 12))
    rate_limit_window_seconds: int = field(default_factory=lambda: _int_env("XIAOMAN_RATE_LIMIT_WINDOW_SECONDS", 60))
    llm_prompt_cost_per_1m: float = field(default_factory=lambda: _float_env("LLM_PROMPT_COST_PER_1M", 0.0))
    llm_completion_cost_per_1m: float = field(
        default_factory=lambda: _float_env("LLM_COMPLETION_COST_PER_1M", 0.0)
    )
    cors_allowed_origins: tuple[str, ...] = field(
        default_factory=lambda: _csv_env(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        )
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
