"""Select the configured SaaS repository backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from app.config import Settings, get_settings
from app.repositories import RepositoryBundle, RepositoryConfigurationError
from app.repositories.file import build_file_repository_bundle
from app.repositories.postgres import build_postgres_repository_bundle


def build_repository_bundle(
    settings: Settings | None = None,
    *,
    data_dir: str | Path | None = None,
    postgres_connect: Callable[[str], Any] | None = None,
) -> RepositoryBundle:
    settings = settings or get_settings()
    backend = settings.storage_backend.strip().lower()
    if backend == "file":
        return build_file_repository_bundle(data_dir)
    if backend == "postgres":
        if not settings.database_url:
            raise RepositoryConfigurationError("DATABASE_URL is required for the postgres storage backend")
        return build_postgres_repository_bundle(settings.database_url, connect=postgres_connect)
    raise RepositoryConfigurationError(f"unsupported storage backend: {settings.storage_backend}")
