"""Repository interfaces for file and PostgreSQL storage backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class SessionRepository(Protocol):
    def create_session(self, tenant_id: str, user_id: str, companion_id: str) -> str:
        ...

    def append_message(self, session_id: str, message: dict[str, Any]) -> None:
        ...

    def list_messages(self, session_id: str) -> list[dict[str, Any]]:
        ...

    def append_chunk(self, session_id: str, chunk: dict[str, Any]) -> None:
        ...

    def list_chunks(self, session_id: str) -> list[dict[str, Any]]:
        ...


class WorldRepository(Protocol):
    def load_layer(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        side: str,
        layer: str,
    ) -> dict[str, Any]:
        ...

    def save_layer(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        side: str,
        layer: str,
        data: dict[str, Any],
    ) -> None:
        ...


class MemoryRepository(Protocol):
    def save_fact(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        fact: dict[str, Any],
    ) -> bool:
        ...

    def search(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        ...

    def save_document(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        category: str,
        document: dict[str, Any],
    ) -> str:
        ...

    def list_documents(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        category: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        ...


class UserRepository(Protocol):
    def load_profile(self, tenant_id: str, user_id: str) -> dict[str, Any]:
        ...

    def save_profile(self, tenant_id: str, user_id: str, profile: dict[str, Any]) -> None:
        ...


class TimelineRepository(Protocol):
    def append_event(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        ...

    def list_events(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True)
class RepositoryBundle:
    backend: str
    ready: bool
    sessions: SessionRepository
    world: WorldRepository
    memory: MemoryRepository
    users: UserRepository
    timeline: TimelineRepository


class RepositoryConfigurationError(RuntimeError):
    """Raised when the selected persistence backend is not configured."""


class RepositoryBackendNotReady(RuntimeError):
    """Raised when a backend boundary exists but its implementation is pending."""


from app.repositories.factory import build_repository_bundle

__all__ = [
    "MemoryRepository",
    "RepositoryBackendNotReady",
    "RepositoryBundle",
    "RepositoryConfigurationError",
    "SessionRepository",
    "TimelineRepository",
    "UserRepository",
    "WorldRepository",
    "build_repository_bundle",
]
