"""Conservative file-to-file guest data migration."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from xiaoman.paths import DATA_DIR


def validate_uuid(value: str) -> str:
    try:
        normalized = str(UUID(value))
    except ValueError as exc:
        raise ValueError("guest id must be a UUID") from exc
    if normalized != value.lower():
        raise ValueError("guest id must use canonical UUID format")
    return normalized


def _merge_missing(target: Any, source: Any) -> Any:
    if isinstance(target, dict) and isinstance(source, dict):
        return {**source, **{key: _merge_missing(target[key], source[key]) if key in source else target[key] for key in target}}
    if isinstance(target, list) and isinstance(source, list):
        rows = list(target)
        seen = {json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows}
        for row in source:
            signature = json.dumps(row, ensure_ascii=False, sort_keys=True)
            if signature not in seen:
                rows.append(row)
                seen.add(signature)
        return rows
    return target


class FileGuestMigrator:
    def __init__(self, data_dir: str = DATA_DIR) -> None:
        self.root = Path(data_dir).resolve()

    def _inside(self, *parts: str) -> Path:
        path = self.root.joinpath(*parts).resolve()
        if path != self.root and self.root not in path.parents:
            raise ValueError("path escapes data directory")
        return path

    def guest_sources(self, guest_id: str) -> list[Path]:
        guest_id = validate_uuid(guest_id)
        candidates = [
            self._inside("users", guest_id),
            self._inside("sessions", f"{guest_id}.json"),
            self._inside("sessions_jsonl", f"{guest_id}.jsonl"),
        ]
        candidates.extend(sorted(self._inside("memory").glob(f"{guest_id}_*")))
        candidates.extend(sorted(self._inside("lineage").glob(f"{guest_id}_*")))
        return [path for path in candidates if path.exists()]

    def has_guest_data(self, guest_id: str) -> bool:
        return bool(self.guest_sources(guest_id))

    def migrate(self, *, guest_id: str, user_id: str, dry_run: bool = False) -> dict[str, Any]:
        guest_id = validate_uuid(guest_id)
        user_id = validate_uuid(user_id)
        if guest_id == user_id:
            return {"status": "completed", "archive_path": "", "files": []}
        sources = self.guest_sources(guest_id)
        if not sources:
            raise FileNotFoundError("guest data not found")

        touched: list[str] = []
        user_source = self._inside("users", guest_id)
        if user_source.exists():
            self._merge_tree(user_source, self._inside("users", user_id), dry_run=dry_run, touched=touched)

        self._merge_file(
            self._inside("sessions", f"{guest_id}.json"),
            self._inside("sessions", f"{user_id}.json"),
            dry_run=dry_run,
            touched=touched,
        )
        self._merge_jsonl(
            self._inside("sessions_jsonl", f"{guest_id}.jsonl"),
            self._inside("sessions_jsonl", f"{user_id}.jsonl"),
            dry_run=dry_run,
            touched=touched,
        )
        self._copy_prefixed("memory", guest_id, user_id, dry_run=dry_run, touched=touched)
        self._copy_prefixed("lineage", guest_id, user_id, dry_run=dry_run, touched=touched)

        if dry_run:
            return {"status": "dry_run", "archive_path": "", "files": touched}

        archive = self._inside("guest_archive", guest_id, datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
        for source in sources:
            if not source.exists():
                continue
            relative = source.relative_to(self.root)
            destination = archive / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
        return {"status": "completed", "archive_path": str(archive), "files": touched}

    def _merge_tree(self, source: Path, target: Path, *, dry_run: bool, touched: list[str]) -> None:
        for source_file in sorted(path for path in source.rglob("*") if path.is_file()):
            self._merge_file(source_file, target / source_file.relative_to(source), dry_run=dry_run, touched=touched)

    def _merge_file(self, source: Path, target: Path, *, dry_run: bool, touched: list[str]) -> None:
        if not source.exists():
            return
        touched.append(str(target.relative_to(self.root)))
        if dry_run:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)
            return
        if source.suffix == ".json":
            with target.open("r", encoding="utf-8") as handle:
                target_data = json.load(handle)
            with source.open("r", encoding="utf-8") as handle:
                source_data = json.load(handle)
            with target.open("w", encoding="utf-8") as handle:
                json.dump(_merge_missing(target_data, source_data), handle, ensure_ascii=False, indent=2)
        elif source.suffix == ".jsonl":
            self._merge_jsonl(source, target, dry_run=False, touched=[])

    def _merge_jsonl(self, source: Path, target: Path, *, dry_run: bool, touched: list[str]) -> None:
        if not source.exists():
            return
        touched.append(str(target.relative_to(self.root)))
        if dry_run:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = target.read_text(encoding="utf-8").splitlines() if target.exists() else []
        rows = list(existing)
        seen = set(existing)
        for line in source.read_text(encoding="utf-8").splitlines():
            if line and line not in seen:
                rows.append(line)
                seen.add(line)
        target.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")

    def _copy_prefixed(self, folder: str, guest_id: str, user_id: str, *, dry_run: bool, touched: list[str]) -> None:
        root = self._inside(folder)
        for source in sorted(root.glob(f"{guest_id}_*")):
            target = source.with_name(f"{user_id}_{source.name[len(guest_id) + 1:]}")
            self._merge_file(source, target, dry_run=dry_run, touched=touched)
