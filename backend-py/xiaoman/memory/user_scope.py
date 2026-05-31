"""用户级记忆路径 — 跨 session 聚合（PRD 4 层存储之结构化/向量层）"""

from __future__ import annotations

import os

from xiaoman.paths import DATA_DIR


def user_memory_dir(user_id: str) -> str:
    path = os.path.join(DATA_DIR, "users", user_id, "memory")
    os.makedirs(path, exist_ok=True)
    return path


def facts_path(user_id: str) -> str:
    return os.path.join(user_memory_dir(user_id), "facts.jsonl")


def organized_path(user_id: str) -> str:
    return os.path.join(user_memory_dir(user_id), "organized.json")


def diary_path(user_id: str) -> str:
    return os.path.join(user_memory_dir(user_id), "diary.jsonl")


def cursor_path(user_id: str) -> str:
    return os.path.join(user_memory_dir(user_id), "extract_cursor.json")


def legacy_session_facts_path(session_id: str) -> str:
    """兼容旧 session 级路径，迁移用"""
    return os.path.join(DATA_DIR, "memory", f"{session_id}_facts.jsonl")
