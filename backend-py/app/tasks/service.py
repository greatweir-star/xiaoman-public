"""Task enqueueing, worker execution, and repository selection."""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import lru_cache
from typing import Any

from app.config import Settings, get_settings
from app.tasks.repository import InMemoryTaskRepository, PostgresTaskRepository, TaskRepository

logger = logging.getLogger(__name__)
TaskHandler = Callable[[dict[str, Any]], dict[str, Any] | None]


class TaskService:
    def __init__(self, repository: TaskRepository, *, retry_delay_seconds: int = 5) -> None:
        self.repository = repository
        self.retry_delay_seconds = max(retry_delay_seconds, 0)

    def enqueue(
        self,
        *,
        tenant_id: str,
        user_id: str | None,
        task_type: str,
        payload: dict[str, Any],
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        return self.repository.enqueue(
            tenant_id=tenant_id,
            user_id=user_id,
            task_type=task_type,
            payload=payload,
            max_attempts=max_attempts,
        )

    def list_for_user(self, tenant_id: str, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self.repository.list_for_user(tenant_id, user_id, min(max(limit, 1), 500))

    def run_once(self, *, worker_id: str, handlers: dict[str, TaskHandler]) -> dict[str, Any] | None:
        task = self.repository.claim_next(worker_id=worker_id)
        if not task:
            return None
        try:
            handler = handlers[str(task["task_type"])]
            result = handler(task) or {}
        except Exception as exc:
            logger.exception("Background task failed: id=%s type=%s", task["id"], task["task_type"])
            self.repository.fail(str(task["id"]), str(exc), retry_delay_seconds=self.retry_delay_seconds)
            return {**task, "status": "retrying_or_failed", "error_message": str(exc)}
        self.repository.complete(str(task["id"]), result)
        return {**task, "status": "completed", "result": result}


def create_task_repository(settings: Settings | None = None) -> TaskRepository:
    resolved = settings or get_settings()
    if resolved.queue_backend.lower() == "inline":
        return InMemoryTaskRepository()
    if resolved.queue_backend.lower() == "postgres":
        if not resolved.database_url:
            raise RuntimeError("DATABASE_URL is required when XIAOMAN_QUEUE_BACKEND=postgres")
        return PostgresTaskRepository(resolved.database_url)
    raise RuntimeError(
        f"Unsupported XIAOMAN_QUEUE_BACKEND={resolved.queue_backend!r}. "
        "Expected 'inline' or 'postgres'."
    )


@lru_cache(maxsize=1)
def get_task_service() -> TaskService:
    return TaskService(create_task_repository())
