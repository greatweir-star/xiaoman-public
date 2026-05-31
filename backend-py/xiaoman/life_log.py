"""小满生活日志 — life_log.jsonl（PRD 日志层，结构化事件流水）"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any

from xiaoman.paths import DATA_DIR


def _xiaoman_dir(user_id: str) -> str:
    path = os.path.join(DATA_DIR, "users", user_id, "xiaoman")
    os.makedirs(path, exist_ok=True)
    return path


def log_path(user_id: str) -> str:
    return os.path.join(_xiaoman_dir(user_id), "life_log.jsonl")


def append_log(
    user_id: str,
    event_type: str,
    summary: str,
    *,
    source: str = "system",
    detail: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """追加一条生活日志事件。"""
    if not user_id:
        return {}
    entry: dict[str, Any] = {
        "id": uuid.uuid4().hex[:12],
        "ts": datetime.now().isoformat(),
        "source": source,
        "event_type": event_type,
        "summary": summary,
    }
    if detail:
        entry["detail"] = detail
    if meta:
        entry["meta"] = meta
    path = log_path(user_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def mirror_timeline_entry(user_id: str, timeline_entry: dict[str, Any]) -> dict[str, Any]:
    """将 life_timeline 条目同步写入 life_log。"""
    if not user_id or not timeline_entry:
        return {}
    event_type = str(timeline_entry.get("type", "timeline"))
    return append_log(
        user_id,
        event_type,
        str(timeline_entry.get("title", "")),
        source="timeline",
        detail=str(timeline_entry.get("detail", "")),
        meta={
            "timeline_id": timeline_entry.get("id"),
            **(timeline_entry.get("meta") or {}),
        },
    )


def list_logs(user_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    """按时间倒序返回生活日志。"""
    path = log_path(user_id)
    if not os.path.exists(path):
        return []
    entries: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    entries.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return entries[:limit]
