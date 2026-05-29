"""小满时段状态机 — PRD Phase 2.1"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PeriodInfo:
    period: str
    energy: int
    reply_style: str
    in_class: bool


# 仅用于 system prompt / 策略，不得原样出现在用户可见回复中
INTERNAL_REPLY_STYLES: frozenset[str] = frozenset(
    {
        "晚安提示，不闲聊",
        "元气但匆忙",
        "紧张、简短",
        "放松、活泼",
        "疲惫、简短",
        "开心、话多",
        "家常、温暖",
        "专注、偶尔抱怨",
        "慵懒、温柔",
        "晚安提示",
    }
)

_PERIOD_TABLE: list[tuple[int, int, str, int, str]] = [
    # (start_minutes, end_minutes, period, energy, reply_style)
    (0, 6 * 60 + 30, "sleep", 0, "晚安提示，不闲聊"),
    (6 * 60 + 30, 8 * 60, "morning", 70, "元气但匆忙"),
    (8 * 60, 12 * 60, "class", 50, "紧张、简短"),
    (12 * 60, 14 * 60, "lunch", 75, "放松、活泼"),
    (14 * 60, 17 * 60 + 30, "class", 45, "疲惫、简短"),
    (17 * 60 + 30, 18 * 60 + 30, "after_class", 80, "开心、话多"),
    (18 * 60 + 30, 19 * 60 + 30, "dinner", 70, "家常、温暖"),
    (19 * 60 + 30, 22 * 60, "homework", 55, "专注、偶尔抱怨"),
    (22 * 60, 22 * 60 + 30, "bedtime", 40, "慵懒、温柔"),
    (22 * 60 + 30, 24 * 60, "sleep", 0, "晚安提示"),
]


def _minutes_now(dt: datetime | None = None) -> int:
    now = dt or datetime.now()
    return now.hour * 60 + now.minute


def get_school_period(dt: datetime | None = None) -> PeriodInfo:
    """根据当前时刻返回 PRD 时段与精力"""
    mins = _minutes_now(dt)
    for start, end, period, energy, style in _PERIOD_TABLE:
        if start <= mins < end:
            return PeriodInfo(
                period=period,
                energy=energy,
                reply_style=style,
                in_class=period == "class",
            )
    return PeriodInfo(period="sleep", energy=0, reply_style="晚安提示", in_class=False)


def is_night_sleep_period(dt: datetime | None = None) -> bool:
    return get_school_period(dt).period == "sleep"
