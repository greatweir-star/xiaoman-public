"""家长模式 — 使用时长限制、夜间锁、密码保护"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from pydantic import BaseModel

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class ParentalConfig(BaseModel):
    enabled: bool = False
    password: str = ""
    daily_limit_minutes: int = 60
    session_limit_minutes: int = 30
    night_start: str = "23:00"
    night_end: str = "06:00"
    crisis_resources_enabled: bool = True


def _config_path(user_id: str) -> str:
    path = os.path.join(DATA_DIR, "users", user_id)
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, "parental.json")


def get_config(user_id: str) -> ParentalConfig:
    """读取家长配置，不存在则返回默认值。"""
    path = _config_path(user_id)
    if not os.path.exists(path):
        return ParentalConfig()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ParentalConfig(**data)
    except (json.JSONDecodeError, TypeError, ValueError):
        return ParentalConfig()


def update_config(user_id: str, config: dict[str, Any], password: str) -> bool:
    """验证密码后更新配置。首次设置（无密码）允许任意密码写入。"""
    current = get_config(user_id)
    # 如果已启用且已设密码，必须验证
    if current.enabled and current.password:
        if password != current.password:
            return False
    # 合并更新
    new_data = current.model_dump()
    new_data.update(config)
    new_cfg = ParentalConfig(**new_data)
    path = _config_path(user_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_cfg.model_dump(), f, ensure_ascii=False, indent=2)
    return True


def _timeline_path(user_id: str) -> str:
    return os.path.join(DATA_DIR, "users", user_id, "xiaoman", "life_timeline.jsonl")


def _parse_time(t: str) -> tuple[int, int]:
    """解析 HH:MM 为 (hour, minute)。"""
    parts = t.split(":")
    return int(parts[0]), int(parts[1])


def is_night_locked(user_id: str) -> bool:
    """当前时间是否在夜间禁用时段。"""
    cfg = get_config(user_id)
    if not cfg.enabled:
        return False
    now = datetime.now()
    sh, sm = _parse_time(cfg.night_start)
    eh, em = _parse_time(cfg.night_end)
    start_min = sh * 60 + sm
    end_min = eh * 60 + em
    now_min = now.hour * 60 + now.minute
    if start_min < end_min:
        return start_min <= now_min < end_min
    return now_min >= start_min or now_min < end_min


def check_usage_limits(user_id: str) -> dict[str, Any]:
    """返回今日使用统计和剩余额度。"""
    cfg = get_config(user_id)
    if not cfg.enabled:
        return {
            "daily_used": 0,
            "daily_remaining": cfg.daily_limit_minutes,
            "session_used": 0,
            "session_remaining": cfg.session_limit_minutes,
            "night_locked": False,
        }

    # 从时间线统计今日 chat 事件
    path = _timeline_path(user_id)
    today_str = datetime.now().strftime("%Y-%m-%d")
    chat_count = 0
    first_chat_ts: datetime | None = None
    last_chat_ts: datetime | None = None

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts_str = entry.get("ts", "")
                if not ts_str.startswith(today_str):
                    continue
                if entry.get("type") == "chat":
                    chat_count += 1
                    try:
                        ts = datetime.fromisoformat(ts_str)
                        if first_chat_ts is None or ts < first_chat_ts:
                            first_chat_ts = ts
                        if last_chat_ts is None or ts > last_chat_ts:
                            last_chat_ts = ts
                    except ValueError:
                        pass

    # 每次对话估算 2 分钟
    daily_used = chat_count * 2
    daily_remaining = max(0, cfg.daily_limit_minutes - daily_used)

    # session_used：今日首次到最近一次的时间差，或 0
    session_used = 0
    if first_chat_ts and last_chat_ts:
        session_used = int((last_chat_ts - first_chat_ts).total_seconds() // 60)
        # 如果只有一条，至少算 1 分钟
        if session_used == 0 and chat_count > 0:
            session_used = 1

    session_remaining = max(0, cfg.session_limit_minutes - session_used)

    return {
        "daily_used": daily_used,
        "daily_remaining": daily_remaining,
        "session_used": session_used,
        "session_remaining": session_remaining,
        "night_locked": is_night_locked(user_id),
    }
