"""Storage repository interfaces shared by file and PostgreSQL backends."""

from __future__ import annotations

from typing import Any, Protocol


class SessionRepository(Protocol):
    def get_or_create_session(self, tenant_id: str, user_id: str, companion_id: str) -> str:
        ...

    def create_session(self, tenant_id: str, user_id: str, companion_id: str) -> str:
        ...

    def append_message(self, session_id: str, message: dict[str, Any]) -> None:
        ...

    def load_messages(self, session_id: str) -> list[dict[str, Any]]:
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


class TimelineRepository(Protocol):
    def append_event(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        event: dict[str, Any],
    ) -> None:
        ...

    def list_events(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        limit: int = 80,
    ) -> list[dict[str, Any]]:
        ...


class UsageRepository(Protocol):
    def record(self, record: dict[str, Any]) -> None:
        ...

    def list_for_user(self, tenant_id: str, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        ...


class RepositoryBundle(Protocol):
    sessions: SessionRepository
    world: WorldRepository
    memory: MemoryRepository
    timeline: TimelineRepository
    usage: UsageRepository
