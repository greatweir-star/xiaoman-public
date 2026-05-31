"""记忆 V0.2 / Sprint B-C — 情绪天气、成长节点、危机干预"""

import os
import shutil
import tempfile

import pytest

from xiaoman.dialogue.crisis import check_crisis
from xiaoman.dialogue.triggers import check_phase0_triggers
from xiaoman.memory.insight_updater import InsightUpdater
from xiaoman.world.world_system import WorldSystem


@pytest.fixture
def world_tmp(monkeypatch):
    tmp = tempfile.mkdtemp()
    data = os.path.join(tmp, "data")
    users = os.path.join(data, "users")
    templates = os.path.join(data, "templates")
    os.makedirs(users, exist_ok=True)
    os.makedirs(templates, exist_ok=True)
    src_templates = os.path.join(
        os.path.dirname(__file__), "..", "data", "templates"
    )
    if os.path.isdir(src_templates):
        for name in os.listdir(src_templates):
            shutil.copy(
                os.path.join(src_templates, name),
                os.path.join(templates, name),
            )
    import xiaoman.world.world_system as ws_mod

    monkeypatch.setattr(ws_mod, "DATA_DIR", data)
    monkeypatch.setattr(ws_mod, "TEMPLATES_DIR", templates)
    w = WorldSystem("v02_test_user")
    yield w
    shutil.rmtree(tmp, ignore_errors=True)


def test_crisis_self_harm_triggers():
    r = check_crisis("我真的不想活了")
    assert r.triggered is True
    assert r.category == "self_harm"
    assert "400-161-9995" in r.reply


def test_crisis_normal_chat():
    assert check_crisis("今天作业好多").triggered is False


def test_phase0_rest_reminder_at_15_turns(monkeypatch):
    monkeypatch.setattr(
        "xiaoman.dialogue.triggers.is_night_sleep_period",
        lambda dt=None: False,
    )
    r = check_phase0_triggers(
        user_message="嗨",
        message_count=15,
        user_emotion="平静",
        rest_round_warn=True,
    )
    assert r.rest_reminder is True


def test_growth_moment_heuristic(world_tmp):
    updater = InsightUpdater()
    changes = updater.update_after_turn(
        world_tmp,
        user_text="月考进步了二十名！",
        assistant_text="太棒了",
        detected_emotion="开心",
    )
    assert "growth_moment" in changes
    moments = world_tmp.l7_profile.list_growth_moments()
    assert len(moments) >= 1
    assert "月考" in moments[-1]["summary"]


def test_emotional_weather_updates(world_tmp):
    updater = InsightUpdater()
    updater.update_after_turn(
        world_tmp,
        user_text="因为和妈妈吵架好烦",
        assistant_text="抱抱",
        detected_emotion="烦躁",
    )
    weather = world_tmp.l7_profile.get_emotional_weather()
    assert weather.get("last_mood") == "烦躁"
    assert weather.get("trigger")
