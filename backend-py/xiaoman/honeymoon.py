"""新手蜜月期 — 前 N 天提升记忆召回精度（PRD 能力树冷启动）"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from xiaoman.dialogue.config import load_dialogue_config


def _meta_path(user_data_dir: str) -> str:
    return os.path.join(user_data_dir, "world_meta.json")


def ensure_first_seen(user_data_dir: str) -> str:
    """记录用户首次进入世界的时间（幂等）。"""
    path = _meta_path(user_data_dir)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ts = data.get("first_seen_at")
        if ts:
            return str(ts)
    now = datetime.now(timezone.utc).isoformat()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {"first_seen_at": now}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            payload = {**json.load(f), **payload}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return now


def is_honeymoon_active(
    user_data_dir: str,
    *,
    reference: datetime | None = None,
) -> bool:
    cfg = load_dialogue_config().get("honeyMoon", {})
    if cfg.get("enabled") is False:
        return False
    days = int(cfg.get("days", 3))
    path = _meta_path(user_data_dir)
    if not os.path.exists(path):
        return True
    with open(path, "r", encoding="utf-8") as f:
        first_seen = json.load(f).get("first_seen_at", "")
    if not first_seen:
        return True
    ref = reference or datetime.now(timezone.utc)
    try:
        started = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    delta_days = (ref.astimezone(timezone.utc) - started.astimezone(timezone.utc)).days
    return delta_days < days


def recall_top_k(user_data_dir: str, default: int = 3) -> int:
    cfg = load_dialogue_config().get("honeyMoon", {})
    boosted = int(cfg.get("recallTopK", 5))
    if is_honeymoon_active(user_data_dir):
        return boosted
    return default
