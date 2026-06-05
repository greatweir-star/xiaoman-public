"""SaaS repository boundary regression tests."""

from datetime import datetime, timezone

import pytest

from app.config import Settings
from app.repositories import RepositoryConfigurationError, build_repository_bundle


class ScriptedCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query, params=()):
        normalized = " ".join(query.split())
        self.connection.queries.append((normalized, params))

    def fetchone(self):
        return self.connection.fetchone_results.pop(0) if self.connection.fetchone_results else None

    def fetchall(self):
        return self.connection.fetchall_results.pop(0) if self.connection.fetchall_results else []


class ScriptedConnection:
    def __init__(self):
        self.queries = []
        self.fetchone_results = []
        self.fetchall_results = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def cursor(self):
        return ScriptedCursor(self)


def test_file_repository_bundle_persists_core_records(tmp_path):
    repositories = build_repository_bundle(Settings(storage_backend="file"), data_dir=tmp_path)

    assert repositories.backend == "file"
    assert repositories.ready is True

    repositories.users.save_profile("tenant-1", "user-1", {"grade": 8})
    assert repositories.users.load_profile("tenant-1", "user-1") == {"grade": 8}

    repositories.world.save_layer("tenant-1", "user-1", "companion-1", "user", "l1", {"name": "Alice"})
    assert repositories.world.load_layer("tenant-1", "user-1", "companion-1", "user", "l1") == {"name": "Alice"}

    session_id = repositories.sessions.create_session("tenant-1", "user-1", "companion-1")
    repositories.sessions.append_message(session_id, {"sender": "user", "text": "hello"})
    assert repositories.sessions.list_messages(session_id) == [{"sender": "user", "text": "hello"}]
    repositories.sessions.append_chunk(session_id, {"kind": "user", "payload": {"content": "hello"}})
    assert repositories.sessions.list_chunks(session_id) == [{"kind": "user", "payload": {"content": "hello"}}]

    assert repositories.memory.save_fact("tenant-1", "user-1", "companion-1", {"content": "likes music"}) is True
    assert repositories.memory.save_fact("tenant-1", "user-1", "companion-1", {"content": "likes music"}) is False
    assert len(repositories.memory.search("tenant-1", "user-1", "companion-1", "music", 3)) == 1
    repositories.memory.save_document("tenant-1", "user-1", "companion-1", "diary", {"content": "today"})
    assert repositories.memory.list_documents("tenant-1", "user-1", "companion-1", "diary", 3)[0]["content"] == "today"

    repositories.timeline.append_event(
        "tenant-1", "user-1", "companion-1", {"type": "chat", "title": "聊天"}
    )
    assert repositories.timeline.list_events("tenant-1", "user-1", "companion-1", 3)[0]["title"] == "聊天"


def test_file_repository_rejects_path_traversal(tmp_path):
    repositories = build_repository_bundle(Settings(storage_backend="file"), data_dir=tmp_path)

    with pytest.raises(ValueError):
        repositories.users.save_profile("tenant-1", "../user-1", {"grade": 8})


def test_postgres_repositories_execute_parameterized_crud():
    connection = ScriptedConnection()
    repositories = build_repository_bundle(
        Settings(storage_backend="postgres", database_url="postgresql://xiaoman:test@localhost/xiaoman"),
        postgres_connect=lambda database_url: connection,
    )

    assert repositories.backend == "postgres"
    assert repositories.ready is True

    session_id = repositories.sessions.create_session("tenant-1", "user-1", "companion-1")
    connection.fetchone_results.append(("message-1",))
    repositories.sessions.append_message(session_id, {"sender": "user", "text": "hello"})
    connection.fetchall_results.append([({"sender": "user", "text": "hello"},)])
    assert repositories.sessions.list_messages(session_id) == [{"sender": "user", "text": "hello"}]
    connection.fetchone_results.append(("chunk-1",))
    repositories.sessions.append_chunk(session_id, {"kind": "user", "payload": {"content": "hello"}})
    connection.fetchall_results.append([({"kind": "user", "payload": {"content": "hello"}},)])
    assert repositories.sessions.list_chunks(session_id) == [{"kind": "user", "payload": {"content": "hello"}}]

    repositories.world.save_layer("tenant-1", "user-1", "companion-1", "user", "l1", {"name": "Alice"})
    connection.fetchone_results.append(({"name": "Alice"},))
    assert repositories.world.load_layer("tenant-1", "user-1", "companion-1", "user", "l1") == {"name": "Alice"}

    connection.fetchone_results.append(("fact-1",))
    assert repositories.memory.save_fact(
        "tenant-1", "user-1", "companion-1", {"content": "likes music", "kind": "preference"}
    ) is True
    connection.fetchall_results.append([
        ("fact-1", "likes music", {"kind": "preference"}, datetime(2026, 6, 1, tzinfo=timezone.utc))
    ])
    assert repositories.memory.search("tenant-1", "user-1", "companion-1", "music", 3) == [{
        "id": "fact-1",
        "content": "likes music",
        "kind": "preference",
        "created_at": "2026-06-01T00:00:00+00:00",
    }]
    repositories.memory.save_document("tenant-1", "user-1", "companion-1", "diary", {"id": "diary-1", "content": "today"})
    connection.fetchall_results.append([
        ("diary-1", {"content": "today"}, datetime(2026, 6, 1, 10, tzinfo=timezone.utc))
    ])
    assert repositories.memory.list_documents("tenant-1", "user-1", "companion-1", "diary", 3) == [{
        "id": "diary-1",
        "content": "today",
        "created_at": "2026-06-01T10:00:00+00:00",
    }]

    repositories.users.save_profile("tenant-1", "user-1", {"grade": 8})
    connection.fetchone_results.append(({"grade": 8},))
    assert repositories.users.load_profile("tenant-1", "user-1") == {"grade": 8}

    repositories.timeline.append_event(
        "tenant-1", "user-1", "companion-1", {"id": "event-1", "ts": "2026-06-01T12:00:00+00:00", "type": "chat", "title": "聊天"}
    )
    connection.fetchall_results.append([
        ("event-1", "chat", "聊天", "", {"emotion": "温柔"}, datetime(2026, 6, 1, 12, tzinfo=timezone.utc))
    ])
    assert repositories.timeline.list_events("tenant-1", "user-1", "companion-1", 3) == [{
        "id": "event-1",
        "ts": "2026-06-01T12:00:00+00:00",
        "type": "chat",
        "title": "聊天",
        "detail": "",
        "meta": {"emotion": "温柔"},
    }]

    queries = "\n".join(query for query, _ in connection.queries)
    assert "INSERT INTO chat_sessions" in queries
    assert "INSERT INTO messages" in queries
    assert "INSERT INTO session_chunks" in queries
    assert "INSERT INTO world_layers" in queries
    assert "INSERT INTO memory_facts" in queries
    assert "INSERT INTO memory_documents" in queries
    assert "INSERT INTO user_profiles" in queries
    assert "INSERT INTO life_events" in queries


def test_postgres_backend_requires_database_url():
    with pytest.raises(RepositoryConfigurationError):
        build_repository_bundle(Settings(storage_backend="postgres", database_url=""))
