"""深夜守护 — PRD xiaoman-flows D4"""

from __future__ import annotations

from datetime import datetime


def is_night_hours(hour: int | None = None) -> bool:
    h = hour if hour is not None else datetime.now().hour
    return h >= 23 or h < 6


def build_night_guard_prompt() -> str:
    return (
        "【深夜守护模式】当前为 23:00–06:00。\n"
        "回复要简短温柔，优先催促用户休息，不要主动展开新话题或长篇聊天。\n"
        "可以说「太晚啦快去睡」「明天再聊」，语气像关心你的同桌，不要说教。"
    )
