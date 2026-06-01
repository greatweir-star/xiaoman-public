from app.auth.repository import InMemoryAuthRepository, PostgresAuthRepository, create_auth_repository
from app.config import Settings
from app.guest_claims.repository import (
    FileGuestClaimRepository,
    PostgresGuestClaimRepository,
    create_guest_claim_repository,
)
from app.repositories.factory import get_repositories
from app.repositories.postgres import PostgresRepositories


def test_local_factories_keep_development_backends():
    settings = Settings(storage_backend="file")

    assert isinstance(create_auth_repository(settings), InMemoryAuthRepository)
    assert isinstance(create_guest_claim_repository(settings), FileGuestClaimRepository)


def test_postgres_factories_select_persistent_backends(monkeypatch):
    settings = Settings(storage_backend="postgres", database_url="postgresql://example")

    assert isinstance(create_auth_repository(settings), PostgresAuthRepository)
    assert isinstance(create_guest_claim_repository(settings), PostgresGuestClaimRepository)

    monkeypatch.setenv("XIAOMAN_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    get_repositories.cache_clear()
    try:
        assert isinstance(get_repositories(), PostgresRepositories)
    finally:
        get_repositories.cache_clear()


def test_postgres_factories_require_database_url():
    settings = Settings(storage_backend="postgres", database_url="")

    for factory in (create_auth_repository, create_guest_claim_repository):
        try:
            factory(settings)
        except RuntimeError as exc:
            assert "DATABASE_URL" in str(exc)
        else:
            raise AssertionError("postgres factory must require DATABASE_URL")
