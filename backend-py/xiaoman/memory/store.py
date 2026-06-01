"""Memory Store — 用户级统一存储（facts / organized / diary / cursor）"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime
from typing import Any

from xiaoman.memory.user_scope import (
    cursor_path,
    diary_path,
    facts_path,
    legacy_session_facts_path,
    organized_path,
    user_memory_dir,
)

logger = logging.getLogger(__name__)

from xiaoman.paths import DATA_DIR
DEDUP_WINDOW_SECONDS = 60


def _normalize_fact_text(text: str) -> str:
    return text.strip()


def _fact_identity(fact: str, category: str, layer: str) -> tuple[str, str, str]:
    return (_normalize_fact_text(fact), category, layer)


class MemoryStore:
    """统一记忆存储 — 以 user_id 为主键"""

    def __init__(
        self,
        data_dir: str = DATA_DIR,
        *,
        fact_repository=None,
        tenant_id: str = "default",
        companion_id: str = "xiaoman",
    ):
        self.data_dir = data_dir
        self.fact_repository = fact_repository
        self.tenant_id = tenant_id
        self.companion_id = companion_id
        os.makedirs(os.path.join(data_dir, "memory"), exist_ok=True)

    def _resolve_user_id(self, user_id: str | None, session_id: str | None) -> str:
        if user_id:
            return user_id
        if session_id:
            return session_id
        raise ValueError("user_id or session_id required")

    def migrate_session_to_user(self, session_id: str, user_id: str) -> None:
        """将旧 session 级 facts 迁移到用户目录（一次性）"""
        legacy = legacy_session_facts_path(session_id, self.data_dir)
        if not os.path.exists(legacy):
            return
        target = facts_path(user_id, self.data_dir)
        if os.path.exists(target) and os.path.getsize(target) > 0:
            return
        shutil.copy2(legacy, target)
        logger.info("Migrated facts %s -> user %s", session_id, user_id)

    # --- Facts ---

    def _find_duplicate_fact(
        self,
        user_id: str,
        fact: str,
        category: str,
        layer: str,
        window_seconds: int = DEDUP_WINDOW_SECONDS,
    ) -> dict[str, Any] | None:
        """Same user + normalized content + category + layer within a short window."""
        key = _fact_identity(fact, category, layer)
        if not key[0]:
            return None
        now = datetime.now()

        def matches(entry: dict[str, Any]) -> bool:
            text = entry.get("fact") or entry.get("content", "")
            entry_key = _fact_identity(text, entry.get("category", ""), entry.get("layer", ""))
            if entry_key != key:
                return False
            if window_seconds <= 0:
                return True
            ts = entry.get("timestamp") or entry.get("created_at", "")
            if not ts:
                return True
            try:
                entry_time = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                if entry_time.tzinfo is not None:
                    entry_time = entry_time.replace(tzinfo=None)
            except ValueError:
                return True
            return (now - entry_time).total_seconds() <= window_seconds

        for entry in reversed(self.load_facts(user_id)):
            if matches(entry):
                return entry
        for entry in reversed(self.load_organized(user_id)):
            if matches(entry):
                return entry
        return None

    def save_fact(self, user_id: str, fact: str, category: str = "general", layer: str = "") -> bool:
        """Append a fact. Returns False if an equivalent fact was saved recently."""
        if self._find_duplicate_fact(user_id, fact, category, layer):
            logger.info("Skipped duplicate fact for user %s", user_id)
            return False
        path = facts_path(user_id, self.data_dir)
        obj: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "fact": fact,
            "content": fact,
            "category": category,
            "layer": layer,
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        if self.fact_repository:
            try:
                self.fact_repository.save_fact(
                    self.tenant_id,
                    user_id,
                    self.companion_id,
                    obj,
                )
            except Exception:
                logger.exception("Memory repository save failed for user %s", user_id)
        return True

    def load_facts(self, user_id: str) -> list[dict[str, Any]]:
        rows = self._load_jsonl(facts_path(user_id, self.data_dir))
        if self.fact_repository:
            try:
                repository_rows = self.fact_repository.search(
                    self.tenant_id,
                    user_id,
                    self.companion_id,
                    "",
                    1000,
                )
                seen = {str(row.get("fact") or row.get("content") or "").strip() for row in rows}
                rows.extend(
                    row
                    for row in repository_rows
                    if str(row.get("fact") or row.get("content") or "").strip() not in seen
                )
            except Exception:
                logger.exception("Memory repository load failed for user %s", user_id)
        return rows

    def load_facts_for_date(self, user_id: str, date: str) -> list[dict[str, Any]]:
        facts = self.load_facts(user_id)
        return [f for f in facts if f.get("timestamp", "").startswith(date)]

    # --- Organized ---

    def save_organized(self, user_id: str, memories: list[dict[str, Any]]) -> None:
        path = organized_path(user_id, self.data_dir)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)

    def load_organized(self, user_id: str) -> list[dict[str, Any]]:
        path = organized_path(user_id, self.data_dir)
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def bump_access(self, user_id: str, fact_text: str) -> None:
        """召回命中时增加访问计数"""
        memories = self.load_organized(user_id)
        updated = False
        for mem in memories:
            if mem.get("fact") == fact_text or mem.get("content") == fact_text:
                mem["access_count"] = mem.get("access_count", 0) + 1
                mem["last_accessed"] = datetime.now().isoformat()
                updated = True
                break
        if updated:
            self.save_organized(user_id, memories)

    # --- Diary ---

    def save_diary(self, user_id: str, date: str, content: str) -> None:
        path = diary_path(user_id, self.data_dir)
        obj = {
            "date": date,
            "content": content,
            "created_at": datetime.now().isoformat(),
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def load_diary(self, user_id: str, date: str | None = None) -> list[dict[str, Any]]:
        entries = self._load_jsonl(diary_path(user_id, self.data_dir))
        if date:
            return [e for e in entries if e.get("date") == date]
        return entries

    # --- Cursor（按 session 记录提取进度）---

    def load_cursor(self, user_id: str, session_id: str) -> int:
        path = cursor_path(user_id, self.data_dir)
        if not os.path.exists(path):
            return 0
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return int(data.get(session_id, 0))

    def save_cursor(self, user_id: str, session_id: str, cursor: int) -> None:
        path = cursor_path(user_id, self.data_dir)
        data: dict[str, int] = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        data[session_id] = cursor
        user_memory_dir(user_id, self.data_dir)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def list_user_ids_with_memory(self) -> list[str]:
        users_root = os.path.join(self.data_dir, "users")
        if not os.path.exists(users_root):
            return []
        result = []
        for name in os.listdir(users_root):
            mem_dir = os.path.join(users_root, name, "memory")
            if os.path.isdir(mem_dir) and os.path.exists(os.path.join(mem_dir, "facts.jsonl")):
                result.append(name)
        return result

    @staticmethod
    def _load_jsonl(path: str) -> list[dict[str, Any]]:
        if not os.path.exists(path):
            return []
        entries = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries
