"""Inventory file-backed Xiaoman data before a PostgreSQL migration.

This script is intentionally dry-run only. It produces a stable count and hash
baseline before any write-enabled importer is used against production data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID


def _is_uuid(value: str) -> bool:
    try:
        return str(UUID(value)) == value.lower()
    except ValueError:
        return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files(root: Path, pattern: str) -> list[Path]:
    return sorted(path for path in root.glob(pattern) if path.is_file())


def _sample_paths(root: Path, paths: list[Path], limit: int = 3) -> list[str]:
    return [str(path.relative_to(root)) for path in sorted(paths)[:limit]]


def summarize_data(data_dir: str) -> dict[str, Any]:
    root = Path(data_dir).resolve()
    users_root = root / "users"
    user_dirs = sorted(
        path for path in users_root.iterdir()
        if path.is_dir() and _is_uuid(path.name)
    ) if users_root.exists() else []
    session_files = _files(root, "sessions/*.json")
    jsonl_files = _files(root, "sessions_jsonl/*.jsonl")
    world_files = [path for user_dir in user_dirs for path in _files(user_dir, "user/*.json") + _files(user_dir, "xiaoman/*.json")]
    memory_files = [path for user_dir in user_dirs for path in _files(user_dir, "memory/*")]
    timeline_files = [path for user_dir in user_dirs for path in _files(user_dir, "xiaoman/*timeline*.json*")]
    hashed_files = sorted(set(session_files + jsonl_files + world_files + memory_files + timeline_files))

    return {
        "mode": "dry-run",
        "data_dir": str(root),
        "counts": {
            "users": len(user_dirs),
            "session_snapshots": len(session_files),
            "session_jsonl": len(jsonl_files),
            "world_files": len(world_files),
            "memory_files": len(memory_files),
            "timeline_files": len(timeline_files),
            "hashed_files": len(hashed_files),
        },
        "hashes": {
            str(path.relative_to(root)): _sha256(path)
            for path in hashed_files
        },
        "samples": {
            user_dir.name: {
                "world": _sample_paths(root, _files(user_dir, "user/*.json") + _files(user_dir, "xiaoman/*.json")),
                "memory": _sample_paths(root, _files(user_dir, "memory/*")),
                "timeline": _sample_paths(root, _files(user_dir, "xiaoman/*timeline*.json*")),
            }
            for user_dir in user_dirs
        },
        "skipped_non_uuid_user_dirs": sorted(
            path.name for path in users_root.iterdir()
            if path.is_dir() and not _is_uuid(path.name)
        ) if users_root.exists() else [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run inventory for file-to-PostgreSQL migration")
    parser.add_argument("--data-dir", default="data", help="Xiaoman data directory")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    print(json.dumps(summarize_data(args.data_dir), ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))


if __name__ == "__main__":
    main()
