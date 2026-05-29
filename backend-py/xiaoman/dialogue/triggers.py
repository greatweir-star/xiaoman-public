"""Phase 0 触发检测 — 深夜模式 / 猜心情 / 休息提醒"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date

from xiaoman.dialogue.config import anti_addiction_config, night_mode_enabled, night_mode_message
from xiaoman.dialogue.period import is_night_sleep_period


@dataclass
class Phase0Result:
    blocked: bool = False
    block_reply: str = ""
    block_emotion: str = "困倦"
    is_sleeping: bool = False
    inject_guess_mood: bool = False
    guess_mood_text: str = ""
    strategy_hints: list[str] = field(default_factory=list)
    rest_reminder: bool = False
    session_time_warning: bool = False


def check_phase0_triggers(
    *,
    user_message: str,
    message_count: int,
    user_emotion: str = "",
    session_elapsed_minutes: float = 0.0,
    rest_round_warn: bool = False,
    session_time_warn: bool = False,
) -> Phase0Result:
    """对话前触发检测。message_count 为本 session 已完成的用户轮数。"""
    result = Phase0Result()

    if night_mode_enabled() and is_night_sleep_period():
        if random.random() < 0.1:
            result.strategy_hints.append("深夜时段，用户还在线，可以轻声关心一句再劝睡")
            return result
        result.blocked = True
        result.is_sleeping = True
        result.block_reply = night_mode_message()
        result.block_emotion = "困倦"
        return result

    if message_count > 0 and message_count % 3 == 0 and user_emotion:
        result.inject_guess_mood = True
        result.guess_mood_text = f"等一下，我猜你现在心情是「{user_emotion}」，对不对？"

    ac = anti_addiction_config()
    if ac["enabled"] and rest_round_warn:
        result.rest_reminder = True
        result.strategy_hints.append("用户已连续聊很多轮，自然地关心一下眼睛累不累")

    if ac["enabled"] and session_time_warn:
        result.session_time_warning = True
        mins = int(session_elapsed_minutes) or ac["warn_minutes"]
        result.strategy_hints.append(
            f"用户已连续在线约{mins}分钟，温柔提醒休息一下、看看远处"
        )

    return result


def today_date_str() -> str:
    return date.today().isoformat()
