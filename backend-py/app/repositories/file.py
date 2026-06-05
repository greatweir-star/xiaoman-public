"""File-backed SaaS repositories used during the V0.03 migration."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.repositories import RepositoryBundle
from xiaoman.paths import DATA_DIR


def _segment(value: str) -> str:
    value = str(value).strip()
    if not value or value in {".", ".."} or Path(value).name != value:
        raise ValueError("repository key must be a single path segment")
    return value


def _read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(fallback)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(fallback)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def _append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            try:
                rows.append(json.loads(raw_line))
            except json.JSONDecodeError:
                continue
    return rows


class FileSessionRepository:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, session_id: str) -> Path:
        return self.root / "sessions" / f"{_segment(session_id)}.json"

    def create_session(self, tenant_id: str, user_id: str, companion_id: str) -> str:
        session_id = str(uuid.uuid4())
        _write_json(self._path(session_id), {
            "id": session_id,
            "tenant_id": _segment(tenant_id),
            "user_id": _segment(user_id),
            "companion_id": _segment(companion_id),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
            "chunks": [],
        })
        return session_id

    def append_message(self, session_id: str, message: dict[str, Any]) -> None:
        path = self._path(session_id)
        session = _read_json(path, {})
        if not session:
            raise KeyError(f"session not found: {session_id}")
        messages = list(session.get("messages") or [])
        messages.append(dict(message))
        session["messages"] = messages
        _write_json(path, session)

    def list_messages(self, session_id: str) -> list[dict[str, Any]]:
        session = _read_json(self._path(session_id), {})
        return list(session.get("messages") or [])

    def append_chunk(self, session_id: str, chunk: dict[str, Any]) -> None:
        path = self._path(session_id)
        session = _read_json(path, {})
        if not session:
            raise KeyError(f"session not found: {session_id}")
        chunks = list(session.get("chunks") or [])
        chunks.append(dict(chunk))
        session["chunks"] = chunks
        _write_json(path, session)

    def list_chunks(self, session_id: str) -> list[dict[str, Any]]:
        session = _read_json(self._path(session_id), {})
        return list(session.get("chunks") or [])


class FileWorldRepository:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, tenant_id: str, user_id: str, companion_id: str, side: str, layer: str) -> Path:
        return (
            self.root
            / "tenants"
            / _segment(tenant_id)
            / "users"
            / _segment(user_id)
            / "companions"
            / _segment(companion_id)
            / "world"
            / _segment(side)
            / f"{_segment(layer)}.json"
        )

    def load_layer(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        side: str,
        layer: str,
    ) -> dict[str, Any]:
        return _read_json(self._path(tenant_id, user_id, companion_id, side, layer), {})

    def save_layer(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        side: str,
        layer: str,
        data: dict[str, Any],
    ) -> None:
        _write_json(self._path(tenant_id, user_id, companion_id, side, layer), dict(data))


class FileMemoryRepository:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, tenant_id: str, user_id: str, companion_id: str) -> Path:
        return (
            self.root
            / "tenants"
            / _segment(tenant_id)
            / "users"
            / _segment(user_id)
            / "companions"
            / _segment(companion_id)
            / "memory"
            / "facts.jsonl"
        )

    def save_fact(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        fact: dict[str, Any],
    ) -> bool:
        path = self._path(tenant_id, user_id, companion_id)
        facts = _read_jsonl(path)
        content = str(fact.get("content") or "").strip()
        if not content:
            raise ValueError("memory fact content is required")
        if any(str(row.get("content") or "").strip() == content for row in facts):
            return False
        row = dict(fact)
        row.setdefault("id", str(uuid.uuid4()))
        row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        row["content"] = content
        _append_jsonl(path, row)
        return True

    def search(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        facts = _read_jsonl(self._path(tenant_id, user_id, companion_id))
        normalized = query.strip().lower()
        if normalized:
            facts = [row for row in facts if normalized in str(row.get("content") or "").lower()]
        return list(reversed(facts))[:max(0, top_k)]

    def _documents_path(self, tenant_id: str, user_id: str, companion_id: str, category: str) -> Path:
        return (
            self.root
            / "tenants"
            / _segment(tenant_id)
            / "users"
            / _segment(user_id)
            / "companions"
            / _segment(companion_id)
            / "memory"
            / f"{_segment(category)}.jsonl"
        )

    def save_document(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        category: str,
        document: dict[str, Any],
    ) -> str:
        row = dict(document)
        row.setdefault("id", str(uuid.uuid4()))
        row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        _append_jsonl(self._documents_path(tenant_id, user_id, companion_id, category), row)
        return str(row["id"])

    def list_documents(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        category: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        documents = _read_jsonl(self._documents_path(tenant_id, user_id, companion_id, category))
        documents.sort(key=lambda document: str(document.get("created_at") or ""), reverse=True)
        return documents[:max(0, limit)]


class FileUserRepository:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, tenant_id: str, user_id: str) -> Path:
        return self.root / "tenants" / _segment(tenant_id) / "users" / _segment(user_id) / "profile.json"

    def load_profile(self, tenant_id: str, user_id: str) -> dict[str, Any]:
        return _read_json(self._path(tenant_id, user_id), {})

    def save_profile(self, tenant_id: str, user_id: str, profile: dict[str, Any]) -> None:
        _write_json(self._path(tenant_id, user_id), dict(profile))


class FileTimelineRepository:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, tenant_id: str, user_id: str, companion_id: str) -> Path:
        return (
            self.root
            / "tenants"
            / _segment(tenant_id)
            / "users"
            / _segment(user_id)
            / "companions"
            / _segment(companion_id)
            / "timeline"
            / "events.jsonl"
        )

    def append_event(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        entry = dict(event)
        entry.setdefault("id", uuid.uuid4().hex[:12])
        entry.setdefault("ts", datetime.now(timezone.utc).isoformat())
        entry.setdefault("type", "event")
        entry.setdefault("title", "")
        entry.setdefault("detail", "")
        _append_jsonl(self._path(tenant_id, user_id, companion_id), entry)
        return entry

    def list_events(
        self,
        tenant_id: str,
        user_id: str,
        companion_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        events = _read_jsonl(self._path(tenant_id, user_id, companion_id))
        events.sort(key=lambda event: str(event.get("ts") or ""), reverse=True)
        return events[:max(0, limit)]


def build_file_repository_bundle(data_dir: str | Path | None = None) -> RepositoryBundle:
    root = Path(data_dir or DATA_DIR) / "saas"
    return RepositoryBundle(
        backend="file",
        ready=True,
        sessions=FileSessionRepository(root),
        world=FileWorldRepository(root),
        memory=FileMemoryRepository(root),
        users=FileUserRepository(root),
        timeline=FileTimelineRepository(root),
    )
