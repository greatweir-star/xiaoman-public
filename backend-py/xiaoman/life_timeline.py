"""小满生活时间线 — JSONL 持久化与查询（PRD 生活日志 / L3 事件）"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

from xiaoman.paths import DATA_DIR

logger = logging.getLogger(__name__)
_repository = None
_tenant_id = "default"
_companion_id = "xiaoman"

_PERIOD_LABELS: dict[str, str] = {
    "sleep": "休息",
    "morning": "早晨",
    "class": "上课",
    "lunch": "午休",
    "after_class": "放学",
    "dinner": "晚饭",
    "homework": "写作业",
    "bedtime": "睡前",
}


def _xiaoman_dir(user_id: str) -> str:
    path = os.path.join(DATA_DIR, "users", user_id, "xiaoman")
    os.makedirs(path, exist_ok=True)
    return path


def timeline_path(user_id: str) -> str:
    return os.path.join(_xiaoman_dir(user_id), "life_timeline.jsonl")


def _state_path(user_id: str) -> str:
    return os.path.join(_xiaoman_dir(user_id), "timeline_state.json")


def period_label(period: str) -> str:
    return _PERIOD_LABELS.get(period, period)


def configure_timeline_repository(repository, *, tenant_id: str = "default", companion_id: str = "xiaoman") -> None:
    """Enable repository-backed timeline reads and dual writes."""
    global _repository, _tenant_id, _companion_id
    _repository = repository
    _tenant_id = tenant_id
    _companion_id = companion_id


def append_event(
    user_id: str,
    event_type: str,
    title: str,
    *,
    detail: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """追加一条时间线事件，返回写入的条目。"""
    if not user_id:
        return {}
    entry: dict[str, Any] = {
        "id": uuid.uuid4().hex[:12],
        "ts": datetime.now().isoformat(),
        "type": event_type,
        "title": title,
        "detail": detail,
    }
    if meta:
        entry["meta"] = meta
    path = timeline_path(user_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    if _repository:
        try:
            _repository.append_event(_tenant_id, user_id, _companion_id, entry)
        except Exception:
            logger.exception("Timeline repository append failed for user %s", user_id)
    try:
        from xiaoman.life_log import mirror_timeline_entry

        mirror_timeline_entry(user_id, entry)
    except Exception:
        pass
    return entry


def list_events(user_id: str, *, limit: int = 80) -> list[dict[str, Any]]:
    """按时间倒序返回时间线条目。"""
    if _repository:
        try:
            rows = _repository.list_events(_tenant_id, user_id, _companion_id, limit)
            if rows:
                return [_normalize_repository_event(row) for row in rows]
        except Exception:
            logger.exception("Timeline repository read failed for user %s", user_id)
    path = timeline_path(user_id)
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


def _normalize_repository_event(row: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    created_at = row.get("created_at")
    ts = metadata.pop("ts", None) or (created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at or ""))
    entry = {
        "id": str(row.get("id") or ""),
        "ts": ts,
        "type": str(row.get("type") or "general"),
        "title": str(row.get("title") or ""),
        "detail": str(row.get("detail") or ""),
    }
    meta = metadata.pop("meta", None)
    if meta:
        entry["meta"] = meta
    return entry


def record_period_if_changed(user_id: str, period: str) -> dict[str, Any] | None:
    """时段变化时写入时间线（去重）。"""
    if not user_id:
        return None
    state_path = _state_path(user_id)
    last = ""
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                last = json.load(f).get("last_period", "")
        except (json.JSONDecodeError, OSError):
            last = ""
    if last == period:
        return None
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump({"last_period": period, "updated_at": datetime.now().isoformat()}, f)
    label = period_label(period)
    activity = f"进入{label}时段"
    return append_event(
        user_id,
        "period",
        activity,
        detail=f"当前时段：{label}",
        meta={"period": period},
    )
