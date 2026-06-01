"""PostgreSQL-backed SaaS repositories."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from psycopg import Connection, connect
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


class PostgresRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self) -> Connection:
        return connect(self.database_url, row_factory=dict_row)


class PostgresSessionRepository(PostgresRepository):
    def get_or_create_session(self, tenant_id: str, user_id: str, companion_id: str) -> str:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM chat_sessions
                WHERE tenant_id = %s AND user_id = %s AND companion_id = %s
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                (tenant_id, user_id, companion_id),
            )
            row = cursor.fetchone()
        return str(row["id"]) if row else self.create_session(tenant_id, user_id, companion_id)

    def create_session(self, tenant_id: str, user_id: str, companion_id: str) -> str:
        session_id = str(uuid.uuid4())
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_sessions (id, tenant_id, user_id, companion_id)
                VALUES (%s, %s, %s, %s)
                """,
                (session_id, tenant_id, user_id, companion_id),
            )
        return session_id

    def append_message(self, session_id: str, message: dict[str, Any]) -> None:
        message_id = str(message.get("id") or uuid.uuid4())
        role = str(message.get("role") or "")
        content = str(message.get("content") or "")
        metadata = {key: value for key, value in message.items() if key not in {"id", "role", "content"}}
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_messages (id, session_id, role, content, metadata)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (message_id, session_id, role, content, Jsonb(metadata)),
            )
            cursor.execute("UPDATE chat_sessions SET updated_at = now() WHERE id = %s", (session_id,))

    def load_messages(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, role, content, metadata, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at, id
                """,
                (session_id,),
            )
            return list(cursor.fetchall())


class PostgresWorldRepository(PostgresRepository):
    def load_layer(self, tenant_id: str, user_id: str, companion_id: str, side: str, layer: str) -> dict[str, Any]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT data
                FROM world_layers
                WHERE tenant_id = %s AND user_id = %s AND companion_id = %s AND side = %s AND layer = %s
                """,
                (tenant_id, user_id, companion_id, side, layer),
            )
            row = cursor.fetchone()
            return dict(row["data"]) if row else {}

    def save_layer(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        side: str,
        layer: str,
        data: dict[str, Any],
    ) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO world_layers (tenant_id, user_id, companion_id, side, layer, data)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, user_id, companion_id, side, layer)
                DO UPDATE SET data = EXCLUDED.data, version = world_layers.version + 1, updated_at = now()
                """,
                (tenant_id, user_id, companion_id, side, layer, Jsonb(data)),
            )


class PostgresMemoryRepository(PostgresRepository):
    def save_fact(self, tenant_id: str, user_id: str, companion_id: str, fact: dict[str, Any]) -> bool:
        content = str(fact.get("fact") or fact.get("content") or "").strip()
        if not content:
            return False
        metadata = {key: value for key, value in fact.items() if key not in {"fact", "content"}}
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM memory_facts
                WHERE tenant_id = %s AND user_id = %s AND companion_id = %s AND content = %s
                LIMIT 1
                """,
                (tenant_id, user_id, companion_id, content),
            )
            if cursor.fetchone():
                return False
            cursor.execute(
                """
                INSERT INTO memory_facts (id, tenant_id, user_id, companion_id, content, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (str(uuid.uuid4()), tenant_id, user_id, companion_id, content, Jsonb(metadata)),
            )
        return True

    def search(self, tenant_id: str, user_id: str, companion_id: str, query: str, top_k: int) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, content AS fact, metadata, created_at
                FROM memory_facts
                WHERE tenant_id = %s AND user_id = %s AND companion_id = %s AND content ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (tenant_id, user_id, companion_id, f"%{query.strip()}%", max(top_k, 0)),
            )
            return [
                {
                    "id": row["id"],
                    "fact": row["fact"],
                    "content": row["fact"],
                    **dict(row.get("metadata") or {}),
                    "created_at": row["created_at"],
                }
                for row in cursor.fetchall()
            ]


class PostgresTimelineRepository(PostgresRepository):
    def append_event(self, tenant_id: str, user_id: str, companion_id: str, event: dict[str, Any]) -> None:
        event_id = str(event.get("id") or uuid.uuid4())
        event_type = str(event.get("type") or "general")
        title = str(event.get("title") or "")
        detail = str(event.get("detail") or "")
        metadata = {key: value for key, value in event.items() if key not in {"id", "type", "title", "detail"}}
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO life_events (id, tenant_id, user_id, companion_id, event_type, title, detail, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (event_id, tenant_id, user_id, companion_id, event_type, title, detail, Jsonb(metadata)),
            )

    def list_events(self, tenant_id: str, user_id: str, companion_id: str, limit: int = 80) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, event_type AS type, title, detail, metadata, created_at
                FROM life_events
                WHERE tenant_id = %s AND user_id = %s AND companion_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (tenant_id, user_id, companion_id, max(limit, 0)),
            )
            return list(cursor.fetchall())


class PostgresUsageRepository(PostgresRepository):
    def record(self, record: dict[str, Any]) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO usage_records (
                    id, tenant_id, user_id, session_id, provider, model, request_type,
                    prompt_tokens, completion_tokens, embedding_tokens, image_count,
                    cost_estimate, latency_ms, status, metadata, created_at
                )
                VALUES (
                    %(id)s, %(tenant_id)s, %(user_id)s, %(session_id)s, %(provider)s, %(model)s, %(request_type)s,
                    %(prompt_tokens)s, %(completion_tokens)s, %(embedding_tokens)s, %(image_count)s,
                    %(cost_estimate)s, %(latency_ms)s, %(status)s, %(metadata)s, %(created_at)s
                )
                """,
                {**record, "metadata": Jsonb(record.get("metadata") or {})},
            )

    def list_for_user(self, tenant_id: str, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, tenant_id, user_id, session_id, provider, model, request_type,
                       prompt_tokens, completion_tokens, embedding_tokens, image_count,
                       cost_estimate, latency_ms, status, metadata, created_at
                FROM usage_records
                WHERE tenant_id = %s AND user_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (tenant_id, user_id, max(limit, 0)),
            )
            return list(cursor.fetchall())


@dataclass(frozen=True)
class PostgresRepositories:
    sessions: PostgresSessionRepository
    world: PostgresWorldRepository
    memory: PostgresMemoryRepository
    timeline: PostgresTimelineRepository
    usage: PostgresUsageRepository


def create_postgres_repositories(database_url: str) -> PostgresRepositories:
    return PostgresRepositories(
        sessions=PostgresSessionRepository(database_url),
        world=PostgresWorldRepository(database_url),
        memory=PostgresMemoryRepository(database_url),
        timeline=PostgresTimelineRepository(database_url),
        usage=PostgresUsageRepository(database_url),
    )
