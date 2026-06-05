"""防沉迷与会话计时"""

import time

from xiaoman.dialogue.config import anti_addiction_config
from xiaoman.dialogue.session_timer import ChatSessionTimer
from xiaoman.dialogue.triggers import check_phase0_triggers
from xiaoman.daily_avatar import resolve_daily_avatar


def test_anti_addiction_defaults():
    cfg = anti_addiction_config()
    assert cfg["enabled"] is True
    assert cfg["warn_minutes"] == 30
    assert cfg["warn_rounds"] == 15


def test_rest_round_warn_once():
    timer = ChatSessionTimer()
    assert timer.check_rest_round(14) is False
    assert timer.check_rest_round(15) is True
    assert timer.check_rest_round(20) is False


def test_session_time_warn_once(monkeypatch):
    timer = ChatSessionTimer()
    monkeypatch.setattr(timer, "elapsed_minutes", lambda: 31.0)
    assert timer.check_session_time() is True
    assert timer.check_session_time() is False


def test_phase0_session_time_warning_flag(monkeypatch):
    monkeypatch.setattr(
        "xiaoman.dialogue.triggers.is_night_sleep_period",
        lambda dt=None: False,
    )
    r = check_phase0_triggers(
        user_message="嗨",
        message_count=1,
        user_emotion="平静",
        session_elapsed_minutes=31,
        session_time_warn=True,
    )
    assert r.session_time_warning is True
    assert any("连续在线" in h for h in r.strategy_hints)


def test_phase0_rest_requires_flag(monkeypatch):
    monkeypatch.setattr(
        "xiaoman.dialogue.triggers.is_night_sleep_period",
        lambda dt=None: False,
    )
    r = check_phase0_triggers(
        user_message="嗨",
        message_count=15,
        user_emotion="平静",
        rest_round_warn=False,
    )
    assert r.rest_reminder is False
    r2 = check_phase0_triggers(
        user_message="嗨",
        message_count=15,
        user_emotion="平静",
        rest_round_warn=True,
    )
    assert r2.rest_reminder is True


def test_daily_avatar_deterministic():
    a = resolve_daily_avatar(style="fresh", day="2026-05-27")
    b = resolve_daily_avatar(style="fresh", day="2026-05-27")
    c = resolve_daily_avatar(style="fresh", day="2026-05-28")
    assert a["url"] == b["url"]
    assert a["date"] == "2026-05-27"
    assert "url" in a and "label" in a
    assert c["id"] != a["id"]
