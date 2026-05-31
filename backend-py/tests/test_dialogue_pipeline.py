"""对话生成流水线测试 — 对照《小满对话生成逻辑方案》"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from xiaoman.chunk import ChunkKind, ChunkRow, ChunkTable, user_text_chunk
from xiaoman.dialogue.input_parser import parse_user_input
from xiaoman.dialogue.period import get_school_period
from xiaoman.dialogue.greeting import build_auth_greeting
from xiaoman.dialogue.period import PeriodInfo
from xiaoman.dialogue.post_process import apply_post_process
from xiaoman.dialogue.session_context import (
    count_consecutive_low_mood,
    count_user_turns,
    extract_last_topic,
    extract_session_summary,
)
from xiaoman.dialogue.strategy import build_strategy_prompt
from xiaoman.dialogue.triggers import check_phase0_triggers


def test_parse_vent_intent():
    parsed = parse_user_input("烦死了作业写不完")
    assert parsed.message_type == "emotion"
    assert parsed.intent == "vent"
    assert parsed.emotion in ("烦躁", "疲惫", "焦虑")


def test_period_class_at_school_time():
    dt = datetime(2026, 5, 27, 10, 0)
    period = get_school_period(dt)
    assert period.period == "class"
    assert period.in_class is True


def test_phase0_blocks_sleep_period(monkeypatch):
    monkeypatch.setattr(
        "xiaoman.dialogue.triggers.is_night_sleep_period",
        lambda dt=None: True,
    )
    monkeypatch.setattr(
        "xiaoman.dialogue.triggers.night_mode_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "xiaoman.dialogue.triggers.random.random",
        lambda: 0.5,
    )
    result = check_phase0_triggers(
        user_message="在吗",
        message_count=1,
        user_emotion="平静",
    )
    assert result.blocked is True
    assert result.block_reply


def test_phase0_guess_mood_every_third_turn():
    result = check_phase0_triggers(
        user_message="嗨",
        message_count=3,
        user_emotion="开心",
    )
    assert result.inject_guess_mood is True
    assert "开心" in result.guess_mood_text


def test_strategy_includes_low_mood_hint():
    parsed = parse_user_input("好烦")
    period = get_school_period(datetime(2026, 5, 27, 20, 0))
    block = build_strategy_prompt(
        parsed,
        period,
        "female",
        last_topic="数学作业",
        consecutive_low_mood=3,
    )
    assert "刚才在聊：数学作业" in block
    assert "情绪低落" in block


def test_auth_greeting_class_no_internal_style_labels(monkeypatch):
    import xiaoman.dialogue.greeting as greeting_mod

    world = MagicMock()
    world.l1_identity.get_xiaoman.return_value = {"name": "小满", "custom_name": ""}
    world.l1_identity.get_user.return_value = {"name": ""}
    world.l3_schedule.get_xiaoman.return_value = {"outfit": "校服"}
    monkeypatch.setattr(
        greeting_mod,
        "get_school_period",
        lambda dt=None: PeriodInfo(
            period="class",
            energy=45,
            reply_style="疲惫、简短",
            in_class=True,
        ),
    )

    text, _, sleeping = build_auth_greeting(world, is_first_session=True)
    assert not sleeping
    assert "疲惫、简短" not in text
    assert "紧张、简短" not in text
    assert text.startswith("（偷偷回你）")


def test_post_process_strips_leaked_reply_style_labels():
    parsed = parse_user_input("在吗")
    period = get_school_period(datetime(2026, 5, 27, 15, 0))
    out = apply_post_process(
        "嗯嗯 疲惫、简短 对了",
        period=period,
        parsed=parsed,
        force_quqiu=False,
    )
    assert "疲惫、简短" not in out.text
    assert "嗯嗯" in out.text


def test_post_process_class_prefix():
    parsed = parse_user_input("在吗")
    period = get_school_period(datetime(2026, 5, 27, 10, 0))
    out = apply_post_process(
        "嗯嗯",
        period=period,
        parsed=parsed,
        force_quqiu=False,
    )
    assert out.text.startswith("（偷偷回你）")


def test_post_process_skips_quqiu_on_vent(monkeypatch):
    monkeypatch.setattr(
        "xiaoman.dialogue.post_process.quqiu_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "xiaoman.dialogue.post_process.quqiu_probability",
        lambda: 1.0,
    )
    parsed = parse_user_input("烦死了")
    period = get_school_period(datetime(2026, 5, 27, 20, 0))
    out = apply_post_process("抱抱你", period=period, parsed=parsed)
    assert "~>" not in out.text


def test_session_context_helpers():
    table = ChunkTable(
        rows=(
            ChunkRow(
                kind=ChunkKind.SYSTEM,
                payload={"content": "【对话摘要】之前聊了考试"},
            ),
            user_text_chunk("今天好累"),
            user_text_chunk("还是好累"),
        )
    )
    assert count_user_turns(table) == 2
    assert "考试" in extract_session_summary(table)
    assert extract_last_topic(table) == "还是好累"
    assert count_consecutive_low_mood(table) >= 2
