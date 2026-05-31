"""业务流冒烟测试 — PRD xiaoman-flows-V0.01"""

from datetime import date, timedelta

import pytest

from xiaoman.night_mode import build_night_guard_prompt, is_night_hours
from xiaoman.world.l1_identity import GRADE_NAMES


def test_night_hours_boundaries():
    assert is_night_hours(23)
    assert is_night_hours(0)
    assert is_night_hours(5)
    assert not is_night_hours(6)
    assert not is_night_hours(22)


def test_night_guard_prompt_non_empty():
    assert "深夜" in build_night_guard_prompt()


def test_grade_names_cover_onboarding():
    assert GRADE_NAMES[7] == "初一"
    assert GRADE_NAMES[12] == "高三"


def test_diary_lock_rules():
    from xiaoman.diary_access import annotate_diary_entries

    today = date.today().isoformat()
    old = (date.today() - timedelta(days=5)).isoformat()
    entries = [
        {"date": today, "content": "今天"},
        {"date": old, "content": "五天前"},
    ]
    out_low = annotate_diary_entries(entries, relation_level=1)
    assert out_low[0]["locked"] is False
    assert out_low[1]["locked"] is True
    assert "树洞" in out_low[1]["unlock_hint"]

    out_high = annotate_diary_entries(entries, relation_level=3)
    assert all(not e["locked"] for e in out_high)


def test_identity_art_style_sync(tmp_path, monkeypatch):
    import xiaoman.world.world_system as ws_mod

    monkeypatch.setattr(ws_mod, "DATA_DIR", str(tmp_path))
    from xiaoman.world.world_system import WorldSystem

    world = WorldSystem("c5_style_user")
    world.l1_identity.set_user_art_style("fresh")
    assert world.l1_identity.get_user().get("art_style") == "fresh"
    world.l1_identity.set_user_art_style("korean")
    assert world.l1_identity.get_user().get("art_style") == "korean"


def test_emotion_detected_handler_registered():
    from xiaoman.events.event_bus import EventBus
    from xiaoman.events.handlers import register_memory_event_handlers

    bus = EventBus()
    register_memory_event_handlers(bus)
    assert "emotion_detected" in bus._handlers
