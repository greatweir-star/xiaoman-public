"""Background task repositories for local tests and PostgreSQL workers."""

from __future__ import annotations

import threading
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from psycopg import connect
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TaskRepository(Protocol):
    def enqueue(
        self,
        *,
        tenant_id: str,
        user_id: str | None,
        task_type: str,
        payload: dict[str, Any],
        max_attempts: int,
    ) -> dict[str, Any]:
        ...

    def claim_next(self, *, worker_id: str) -> dict[str, Any] | None:
        ...

    def complete(self, task_id: str, result: dict[str, Any]) -> None:
        ...

    def fail(self, task_id: str, error_message: str, *, retry_delay_seconds: int) -> None:
        ...

    def list_for_user(self, tenant_id: str, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        ...


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def enqueue(
        self,
        *,
        tenant_id: str,
        user_id: str | None,
        task_type: str,
        payload: dict[str, Any],
        max_attempts: int,
    ) -> dict[str, Any]:
        now = _now()
        task = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "task_type": task_type,
            "payload": deepcopy(payload),
            "status": "pending",
            "attempt_count": 0,
            "max_attempts": max(max_attempts, 1),
            "available_at": now,
            "created_at": now,
            "updated_at": now,
        }
        with self._lock:
            self._tasks[task["id"]] = task
        return deepcopy(task)

    def claim_next(self, *, worker_id: str) -> dict[str, Any] | None:
        now = _now()
        with self._lock:
            candidates = [
                task
                for task in self._tasks.values()
                if task["status"] == "pending" and task["available_at"] <= now
            ]
            if not candidates:
                return None
            task = sorted(candidates, key=lambda row: (row["created_at"], row["id"]))[0]
            task.update(
                {
                    "status": "running",
                    "attempt_count": int(task["attempt_count"]) + 1,
                    "locked_at": now,
                    "locked_by": worker_id,
                    "started_at": task.get("started_at") or now,
                    "updated_at": now,
                }
            )
            return deepcopy(task)

    def complete(self, task_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            self._tasks[task_id].update(
                {
                    "status": "completed",
                    "result": deepcopy(result),
                    "completed_at": _now(),
                    "locked_at": None,
                    "locked_by": None,
                    "updated_at": _now(),
                }
            )

    def fail(self, task_id: str, error_message: str, *, retry_delay_seconds: int) -> None:
        with self._lock:
            task = self._tasks[task_id]
            exhausted = int(task["attempt_count"]) >= int(task["max_attempts"])
            now = _now()
            task.update(
                {
                    "status": "failed" if exhausted else "pending",
                    "available_at": now + timedelta(seconds=max(retry_delay_seconds, 0)),
                    "failed_at": now if exhausted else None,
                    "error_message": error_message,
                    "locked_at": None,
                    "locked_by": None,
                    "updated_at": now,
                }
            )

    def list_for_user(self, tenant_id: str, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = [
                deepcopy(task)
                for task in self._tasks.values()
                if task["tenant_id"] == tenant_id and task["user_id"] == user_id
            ]
        rows.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
        return rows[: max(limit, 0)]


class PostgresTaskRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self):
        return connect(self.database_url, row_factory=dict_row)

    def enqueue(
        self,
        *,
        tenant_id: str,
        user_id: str | None,
        task_type: str,
        payload: dict[str, Any],
        max_attempts: int,
    ) -> dict[str, Any]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO background_tasks (id, tenant_id, user_id, task_type, payload, max_attempts)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (str(uuid.uuid4()), tenant_id, user_id, task_type, Jsonb(payload), max(max_attempts, 1)),
            )
            return dict(cursor.fetchone())

    def claim_next(self, *, worker_id: str) -> dict[str, Any] | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                WITH claimed AS (
                    SELECT id
                    FROM background_tasks
                    WHERE status = 'pending' AND available_at <= now()
                    ORDER BY available_at, created_at, id
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE background_tasks AS task
                SET status = 'running',
                    attempt_count = task.attempt_count + 1,
                    locked_at = now(),
                    locked_by = %s,
                    started_at = COALESCE(task.started_at, now()),
                    updated_at = now()
                FROM claimed
                WHERE task.id = claimed.id
                RETURNING task.*
                """,
                (worker_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def complete(self, task_id: str, result: dict[str, Any]) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE background_tasks
                SET status = 'completed', result = %s, completed_at = now(),
                    locked_at = NULL, locked_by = NULL, updated_at = now()
                WHERE id = %s
                """,
                (Jsonb(result), task_id),
            )

    def fail(self, task_id: str, error_message: str, *, retry_delay_seconds: int) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE background_tasks
                SET status = CASE WHEN attempt_count >= max_attempts THEN 'failed' ELSE 'pending' END,
                    available_at = now() + make_interval(secs => %s),
                    failed_at = CASE WHEN attempt_count >= max_attempts THEN now() ELSE NULL END,
                    error_message = %s,
                    locked_at = NULL,
                    locked_by = NULL,
                    updated_at = now()
                WHERE id = %s
                """,
                (max(retry_delay_seconds, 0), error_message[:2000], task_id),
            )

    def list_for_user(self, tenant_id: str, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM background_tasks
                WHERE tenant_id = %s AND user_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (tenant_id, user_id, max(limit, 0)),
            )
            return [dict(row) for row in cursor.fetchall()]
