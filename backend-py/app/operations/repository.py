"""File and PostgreSQL operational event repositories."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Protocol

from psycopg import connect
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


class OperationalEventRepository(Protocol):
    def append(self, record: dict[str, Any]) -> None:
        ...

    def list_for_user(self, tenant_id: str, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        ...


class FileOperationalEventRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def append(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def list_for_user(self, tenant_id: str, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("tenant_id") == tenant_id and row.get("user_id") == user_id:
                    rows.append(row)
        rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
        return rows[: max(limit, 0)]


class PostgresOperationalEventRepository:
    def __init__(self, database_url: str, table: str) -> None:
        if table not in {"audit_logs", "safety_events"}:
            raise ValueError("unsupported operational table")
        self.database_url = database_url
        self.table = table

    def _connect(self):
        return connect(self.database_url, row_factory=dict_row)

    def append(self, record: dict[str, Any]) -> None:
        columns = {
            "audit_logs": ("id", "tenant_id", "user_id", "action", "resource", "status", "metadata", "created_at"),
            "safety_events": ("id", "tenant_id", "user_id", "category", "severity", "source", "status", "metadata", "created_at"),
        }[self.table]
        placeholders = ", ".join(f"%({column})s" for column in columns)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders})",
                {**record, "metadata": Jsonb(record.get("metadata") or {})},
            )

    def list_for_user(self, tenant_id: str, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *
                FROM {self.table}
                WHERE tenant_id = %s AND user_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (tenant_id, user_id, max(limit, 0)),
            )
            return [dict(row) for row in cursor.fetchall()]
