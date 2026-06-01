"""Repository backend selection."""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.repositories.file import FileRepositories, create_file_repositories
from app.repositories.postgres import PostgresRepositories, create_postgres_repositories


@lru_cache(maxsize=1)
def get_repositories() -> FileRepositories | PostgresRepositories:
    settings = get_settings()
    if settings.storage_backend.lower() == "file":
        return create_file_repositories()
    if settings.storage_backend.lower() == "postgres":
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is required when XIAOMAN_STORAGE_BACKEND=postgres")
        return create_postgres_repositories(settings.database_url)
    raise RuntimeError(
        f"Unsupported XIAOMAN_STORAGE_BACKEND={settings.storage_backend!r}. "
        "Expected 'file' or 'postgres'."
    )
