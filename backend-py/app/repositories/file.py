"""File-backed repositories used by local development and migration tooling."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from xiaoman.paths import DATA_DIR


def _safe(value: str) -> str:
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError("repository key must be a non-empty path segment")
    return value


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


@dataclass(frozen=True)
class FileRepositoryPaths:
    root: Path

    def scoped(self, tenant_id: str, user_id: str, companion_id: str) -> Path:
        return self.root / "repository" / _safe(tenant_id) / _safe(user_id) / _safe(companion_id)


class FileSessionRepository:
    def __init__(self, paths: FileRepositoryPaths) -> None:
        self.paths = paths

    def create_session(self, tenant_id: str, user_id: str, companion_id: str) -> str:
        session_id = str(uuid.uuid4())
        path = self.paths.root / "repository_sessions" / f"{session_id}.jsonl"
        _append_jsonl(
            path,
            {
                "type": "header",
                "session_id": session_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "companion_id": companion_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return session_id

    def get_or_create_session(self, tenant_id: str, user_id: str, companion_id: str) -> str:
        index_path = self.paths.root / "repository_sessions" / "index.json"
        index = _read_json(index_path, {})
        key = f"{_safe(tenant_id)}:{_safe(user_id)}:{_safe(companion_id)}"
        if key in index:
            return str(index[key])
        session_id = self.create_session(tenant_id, user_id, companion_id)
        index[key] = session_id
        _write_json(index_path, index)
        return session_id

    def append_message(self, session_id: str, message: dict[str, Any]) -> None:
        path = self.paths.root / "repository_sessions" / f"{_safe(session_id)}.jsonl"
        _append_jsonl(path, {"type": "message", **message})

    def load_messages(self, session_id: str) -> list[dict[str, Any]]:
        path = self.paths.root / "repository_sessions" / f"{_safe(session_id)}.jsonl"
        return [row for row in _read_jsonl(path) if row.get("type") == "message"]


class FileWorldRepository:
    def __init__(self, paths: FileRepositoryPaths) -> None:
        self.paths = paths

    def _path(self, tenant_id: str, user_id: str, companion_id: str, side: str, layer: str) -> Path:
        return self.paths.scoped(tenant_id, user_id, companion_id) / "world" / _safe(side) / f"{_safe(layer)}.json"

    def load_layer(self, tenant_id: str, user_id: str, companion_id: str, side: str, layer: str) -> dict[str, Any]:
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
        _write_json(self._path(tenant_id, user_id, companion_id, side, layer), data)


class FileMemoryRepository:
    def __init__(self, paths: FileRepositoryPaths) -> None:
        self.paths = paths

    def _path(self, tenant_id: str, user_id: str, companion_id: str) -> Path:
        return self.paths.scoped(tenant_id, user_id, companion_id) / "memory" / "facts.jsonl"

    def save_fact(self, tenant_id: str, user_id: str, companion_id: str, fact: dict[str, Any]) -> bool:
        path = self._path(tenant_id, user_id, companion_id)
        normalized = str(fact.get("fact") or fact.get("content") or "").strip()
        if not normalized:
            return False
        if any(str(row.get("fact") or row.get("content") or "").strip() == normalized for row in _read_jsonl(path)):
            return False
        _append_jsonl(path, {"created_at": datetime.now(timezone.utc).isoformat(), **fact, "fact": normalized})
        return True

    def search(self, tenant_id: str, user_id: str, companion_id: str, query: str, top_k: int) -> list[dict[str, Any]]:
        needle = query.strip().lower()
        rows = _read_jsonl(self._path(tenant_id, user_id, companion_id))
        if needle:
            rows = [row for row in rows if needle in str(row.get("fact") or row.get("content") or "").lower()]
        return rows[-max(top_k, 0) :]


class FileTimelineRepository:
    def __init__(self, paths: FileRepositoryPaths) -> None:
        self.paths = paths

    def _path(self, tenant_id: str, user_id: str, companion_id: str) -> Path:
        return self.paths.scoped(tenant_id, user_id, companion_id) / "timeline" / "events.jsonl"

    def append_event(self, tenant_id: str, user_id: str, companion_id: str, event: dict[str, Any]) -> None:
        _append_jsonl(self._path(tenant_id, user_id, companion_id), event)

    def list_events(self, tenant_id: str, user_id: str, companion_id: str, limit: int = 80) -> list[dict[str, Any]]:
        rows = _read_jsonl(self._path(tenant_id, user_id, companion_id))
        rows.sort(key=lambda row: str(row.get("ts") or row.get("created_at") or ""), reverse=True)
        return rows[: max(limit, 0)]


class FileUsageRepository:
    def __init__(self, paths: FileRepositoryPaths) -> None:
        self.paths = paths

    def _path(self, tenant_id: str, user_id: str) -> Path:
        return self.paths.root / "repository" / _safe(tenant_id) / _safe(user_id) / "usage" / "records.jsonl"

    def record(self, record: dict[str, Any]) -> None:
        _append_jsonl(self._path(str(record["tenant_id"]), str(record["user_id"])), record)

    def list_for_user(self, tenant_id: str, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = _read_jsonl(self._path(tenant_id, user_id))
        rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
        return rows[: max(limit, 0)]


@dataclass(frozen=True)
class FileRepositories:
    sessions: FileSessionRepository
    world: FileWorldRepository
    memory: FileMemoryRepository
    timeline: FileTimelineRepository
    usage: FileUsageRepository


def create_file_repositories(data_dir: str = DATA_DIR) -> FileRepositories:
    paths = FileRepositoryPaths(Path(data_dir))
    return FileRepositories(
        sessions=FileSessionRepository(paths),
        world=FileWorldRepository(paths),
        memory=FileMemoryRepository(paths),
        timeline=FileTimelineRepository(paths),
        usage=FileUsageRepository(paths),
    )
