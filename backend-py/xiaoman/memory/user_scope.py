"""用户级记忆路径 — 跨 session 聚合（PRD 4 层存储之结构化/向量层）"""

from __future__ import annotations

import os

from xiaoman.paths import DATA_DIR


def user_memory_dir(user_id: str, data_dir: str = DATA_DIR) -> str:
    path = os.path.join(data_dir, "users", user_id, "memory")
    os.makedirs(path, exist_ok=True)
    return path


def facts_path(user_id: str, data_dir: str = DATA_DIR) -> str:
    return os.path.join(user_memory_dir(user_id, data_dir), "facts.jsonl")


def organized_path(user_id: str, data_dir: str = DATA_DIR) -> str:
    return os.path.join(user_memory_dir(user_id, data_dir), "organized.json")


def diary_path(user_id: str, data_dir: str = DATA_DIR) -> str:
    return os.path.join(user_memory_dir(user_id, data_dir), "diary.jsonl")


def cursor_path(user_id: str, data_dir: str = DATA_DIR) -> str:
    return os.path.join(user_memory_dir(user_id, data_dir), "extract_cursor.json")


def legacy_session_facts_path(session_id: str, data_dir: str = DATA_DIR) -> str:
    """兼容旧 session 级路径，迁移用"""
    return os.path.join(data_dir, "memory", f"{session_id}_facts.jsonl")
