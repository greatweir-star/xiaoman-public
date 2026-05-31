"""Repository interfaces for file and PostgreSQL storage backends."""

from __future__ import annotations

from typing import Any, Protocol


class SessionRepository(Protocol):
    def create_session(self, tenant_id: str, user_id: str, companion_id: str) -> str:
        ...

    def append_message(self, session_id: str, message: dict[str, Any]) -> None:
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

