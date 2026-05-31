"""TC5 情绪承接 — vent 检测与规则兜底"""

from xiaoman.dialogue.emotion_hold import (
    emotion_hold_strategy_hint,
    finalize_assistant_text,
    needs_emotion_hold,
    pick_emotion_hold_fallback,
    should_apply_emotion_hold_fallback,
)
from xiaoman.dialogue.input_parser import parse_user_input
from xiaoman.emotion.detector import EmotionDetector


def test_vent_message_detected_by_emotion_detector():
    det = EmotionDetector(llm_client=None)
    result = det.detect("今天好烦，作业写不完")
    assert result.source == "vent"
    assert result.emotion in ("愤怒", "烦躁", "焦虑", "难过", "疲惫")


def test_parse_today_annoyed_is_vent():
    parsed = parse_user_input("今天好烦")
    assert parsed.intent == "vent"
    assert parsed.message_type == "emotion"


def test_needs_emotion_hold_for_vent():
    parsed = parse_user_input("烦死了")
    assert needs_emotion_hold(parsed)


def test_emotion_hold_strategy_hint_differs_by_gender():
    assert "说教" in emotion_hold_strategy_hint("male")
    assert "抱住" in emotion_hold_strategy_hint("female")


def test_short_reply_triggers_stream_end_fallback():
    parsed = parse_user_input("今天好烦")
    text, used = finalize_assistant_text(
        "嗯",
        "今天好烦",
        parsed,
        user_gender="female",
    )
    assert used is True
    assert len(text) >= 4
    assert should_apply_emotion_hold_fallback("嗯", parsed)


def test_long_reply_skips_fallback():
    parsed = parse_user_input("今天好烦")
    long = "听起来你今天挺不容易的，愿意多说一点吗？"
    text, used = finalize_assistant_text(
        long,
        "今天好烦",
        parsed,
        user_gender="female",
    )
    assert used is False
    assert text == long


def test_pick_fallback_no_crash():
    parsed = parse_user_input("今天好烦")
    text = pick_emotion_hold_fallback(
        "今天好烦",
        parsed,
        user_gender="female",
        user_name="小雨",
    )
    assert len(text) >= 4
    assert "建议" not in text
