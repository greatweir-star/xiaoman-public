"""PostgreSQL-backed SaaS repositories."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Callable

from app.repositories import RepositoryBundle, RepositoryConfigurationError

ConnectionFactory = Callable[[str], Any]


def _default_connect(database_url: str) -> Any:
    try:
        import psycopg
    except ModuleNotFoundError as exc:
        raise RepositoryConfigurationError(
            "psycopg is required for XIAOMAN_STORAGE_BACKEND=postgres; install backend-py requirements"
        ) from exc
    return psycopg.connect(database_url)


def _json_text(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _isoformat(value: Any) -> str:
    return value.isoformat() if isinstance(value, datetime) else str(value or "")


class _PostgresRepository:
    def __init__(self, database_url: str, connect: ConnectionFactory | None = None) -> None:
        self.database_url = database_url
        self.connect = connect or _default_connect

    def _connection(self) -> Any:
        return self.connect(self.database_url)


class PostgresSessionRepository(_PostgresRepository):
    def create_session(self, tenant_id: str, user_id: str, companion_id: str) -> str:
        session_id = str(uuid.uuid4())
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_sessions (id, tenant_id, user_id, companion_id)
                VALUES (%s, %s, %s, %s)
                """,
                (session_id, tenant_id, user_id, companion_id),
            )
        return session_id

    def append_message(self, session_id: str, message: dict[str, Any]) -> None:
        message_id = str(uuid.uuid4())
        sender = str(message.get("sender") or "system")
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO messages (id, tenant_id, session_id, sender, payload)
                SELECT %s, tenant_id, id, %s, %s::jsonb
                FROM chat_sessions
                WHERE id = %s
                RETURNING id
                """,
                (message_id, sender, _json_text(message), session_id),
            )
            if cursor.fetchone() is None:
                raise KeyError(f"session not found: {session_id}")

    def list_messages(self, session_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT payload
                FROM messages
                WHERE session_id = %s
                ORDER BY created_at, id
                """,
                (session_id,),
            )
            return [_json_dict(row[0]) for row in cursor.fetchall()]

    def append_chunk(self, session_id: str, chunk: dict[str, Any]) -> None:
        chunk_id = str(uuid.uuid4())
        kind = str(chunk.get("kind") or "message")
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO session_chunks (id, tenant_id, session_id, kind, payload)
                SELECT %s, tenant_id, id, %s, %s::jsonb
                FROM chat_sessions
                WHERE id = %s
                RETURNING id
                """,
                (chunk_id, kind, _json_text(chunk), session_id),
            )
            if cursor.fetchone() is None:
                raise KeyError(f"session not found: {session_id}")

    def list_chunks(self, session_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT payload
                FROM session_chunks
                WHERE session_id = %s
                ORDER BY created_at, id
                """,
                (session_id,),
            )
            return [_json_dict(row[0]) for row in cursor.fetchall()]


class PostgresWorldRepository(_PostgresRepository):
    def load_layer(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        side: str,
        layer: str,
    ) -> dict[str, Any]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT payload
                FROM world_layers
                WHERE tenant_id = %s AND user_id = %s AND companion_id = %s
                  AND side = %s AND layer = %s
                """,
                (tenant_id, user_id, companion_id, side, layer),
            )
            row = cursor.fetchone()
            return _json_dict(row[0]) if row else {}

    def save_layer(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        side: str,
        layer: str,
        data: dict[str, Any],
    ) -> None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO world_layers (tenant_id, user_id, companion_id, side, layer, payload)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (tenant_id, user_id, companion_id, side, layer)
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = now()
                """,
                (tenant_id, user_id, companion_id, side, layer, _json_text(data)),
            )


class PostgresMemoryRepository(_PostgresRepository):
    def save_fact(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        fact: dict[str, Any],
    ) -> bool:
        content = str(fact.get("content") or "").strip()
        if not content:
            raise ValueError("memory fact content is required")
        fact_id = str(fact.get("id") or uuid.uuid4())
        metadata = {key: value for key, value in fact.items() if key not in {"id", "content", "created_at"}}
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO memory_facts (id, tenant_id, user_id, companion_id, content, metadata)
                SELECT %s, %s, %s, %s, %s, %s::jsonb
                WHERE NOT EXISTS (
                    SELECT 1 FROM memory_facts
                    WHERE tenant_id = %s AND user_id = %s AND companion_id = %s AND content = %s
                )
                RETURNING id
                """,
                (
                    fact_id,
                    tenant_id,
                    user_id,
                    companion_id,
                    content,
                    _json_text(metadata),
                    tenant_id,
                    user_id,
                    companion_id,
                    content,
                ),
            )
            return cursor.fetchone() is not None

    def search(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        normalized = query.strip()
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, content, metadata, created_at
                FROM memory_facts
                WHERE tenant_id = %s AND user_id = %s AND companion_id = %s
                  AND (%s = '' OR content ILIKE %s)
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (tenant_id, user_id, companion_id, normalized, f"%{normalized}%", max(0, top_k)),
            )
            facts: list[dict[str, Any]] = []
            for fact_id, content, metadata, created_at in cursor.fetchall():
                fact = _json_dict(metadata)
                fact.update({"id": str(fact_id), "content": str(content), "created_at": _isoformat(created_at)})
                facts.append(fact)
            return facts

    def save_document(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        category: str,
        document: dict[str, Any],
    ) -> str:
        document_id = str(document.get("id") or uuid.uuid4())
        payload = dict(document)
        payload.pop("id", None)
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO memory_documents (id, tenant_id, user_id, companion_id, category, payload)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (document_id, tenant_id, user_id, companion_id, category, _json_text(payload)),
            )
        return document_id

    def list_documents(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        category: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, payload, created_at
                FROM memory_documents
                WHERE tenant_id = %s AND user_id = %s AND companion_id = %s AND category = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (tenant_id, user_id, companion_id, category, max(0, limit)),
            )
            documents: list[dict[str, Any]] = []
            for document_id, payload, created_at in cursor.fetchall():
                document = _json_dict(payload)
                document.update({"id": str(document_id), "created_at": _isoformat(created_at)})
                documents.append(document)
            return documents


class PostgresUserRepository(_PostgresRepository):
    def load_profile(self, tenant_id: str, user_id: str) -> dict[str, Any]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT profile FROM user_profiles WHERE tenant_id = %s AND user_id = %s",
                (tenant_id, user_id),
            )
            row = cursor.fetchone()
            return _json_dict(row[0]) if row else {}

    def save_profile(self, tenant_id: str, user_id: str, profile: dict[str, Any]) -> None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_profiles (tenant_id, user_id, profile)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (tenant_id, user_id)
                DO UPDATE SET profile = EXCLUDED.profile, updated_at = now()
                """,
                (tenant_id, user_id, _json_text(profile)),
            )


class PostgresTimelineRepository(_PostgresRepository):
    def append_event(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        entry = dict(event)
        entry.setdefault("id", uuid.uuid4().hex[:12])
        entry.setdefault("ts", datetime.now().astimezone().isoformat())
        entry.setdefault("type", "event")
        entry.setdefault("title", "")
        entry.setdefault("detail", "")
        metadata = dict(entry.get("meta") or {})
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO life_events (
                    id, tenant_id, user_id, companion_id, event_type, title, detail, metadata, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                """,
                (
                    entry["id"],
                    tenant_id,
                    user_id,
                    companion_id,
                    entry["type"],
                    entry["title"],
                    entry["detail"],
                    _json_text(metadata),
                    entry["ts"],
                ),
            )
        return entry

    def list_events(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, event_type, title, detail, metadata, created_at
                FROM life_events
                WHERE tenant_id = %s AND user_id = %s AND companion_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (tenant_id, user_id, companion_id, max(0, limit)),
            )
            events: list[dict[str, Any]] = []
            for event_id, event_type, title, detail, metadata, created_at in cursor.fetchall():
                event = {
                    "id": str(event_id),
                    "ts": _isoformat(created_at),
                    "type": str(event_type),
                    "title": str(title),
                    "detail": str(detail or ""),
                }
                parsed_metadata = _json_dict(metadata)
                if parsed_metadata:
                    event["meta"] = parsed_metadata
                events.append(event)
            return events


def build_postgres_repository_bundle(
    database_url: str,
    *,
    connect: ConnectionFactory | None = None,
) -> RepositoryBundle:
    return RepositoryBundle(
        backend="postgres",
        ready=True,
        sessions=PostgresSessionRepository(database_url, connect),
        world=PostgresWorldRepository(database_url, connect),
        memory=PostgresMemoryRepository(database_url, connect),
        users=PostgresUserRepository(database_url, connect),
        timeline=PostgresTimelineRepository(database_url, connect),
    )
