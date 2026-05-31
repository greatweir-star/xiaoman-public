"""Life 技能 tools + L5 精力衰减 — 窄范围回归"""

import json
import os
import shutil
from datetime import date

import pytest

from xiaoman.session import XiaomanSession
from xiaoman.tools.focus_buddy import FocusBuddyTool
from xiaoman.tools.schedule_remind import ScheduleRemindTool
from xiaoman.tools.study_guide import StudyGuideTool
from xiaoman.world.world_system import WorldSystem


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr("xiaoman.world.world_system.DATA_DIR", str(tmp_path))
    user_id = "life_tools_user"
    w = WorldSystem(user_id)
    yield w
    user_dir = os.path.join(tmp_path, "users", user_id)
    if os.path.isdir(user_dir):
        shutil.rmtree(user_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def bind_world_tools(world):
    def get_world(uid: str) -> WorldSystem:
        return world

    ScheduleRemindTool.bind_world(get_world)
    FocusBuddyTool.bind_world(get_world)
    StudyGuideTool.bind_world(get_world)
    yield


def test_turn_energy_decay_on_chat(world):
    world.l5_emotion.update_xiaoman_energy(30)
    before = world.l5_emotion.get_xiaoman()["energy"]
    world.update_from_message("嗯", "好")
    after = world.l5_emotion.get_xiaoman()["energy"]
    assert after < before


def test_auth_energy_decay(world):
    world.l5_emotion.update_xiaoman_energy(20)
    before = world.l5_emotion.get_xiaoman()["energy"]
    result = world.l5_emotion.apply_auth_energy_decay()
    assert result["change"] == "auth_energy_decay"
    assert world.l5_emotion.get_xiaoman()["energy"] == before - 1


def test_xiaoman_context_exposes_energy(world):
    ctx = world.get_xiaoman_context()
    assert "energy" in ctx
    assert ctx["energy"] == ctx["emotion"]["energy"]


def test_schedule_remind_add_and_list(world):
    session = XiaomanSession(id=world.user_id, user_id=world.user_id)
    tool = ScheduleRemindTool()
    raw = tool(session, {"action": "add_reminder", "title": "交物理作业"})
    assert json.loads(raw)["ok"] is True
    listed = json.loads(tool(session, {"action": "list"}))
    assert listed["count"] >= 1
    assert any("物理" in item["text"] for item in listed["items"])


def test_focus_buddy_start_status(world):
    session = XiaomanSession(id=world.user_id, user_id=world.user_id)
    tool = FocusBuddyTool()
    start = json.loads(
        tool(session, {"action": "start", "minutes": 10, "task": "写数学"})
    )
    assert start["active"] is True
    status = json.loads(tool(session, {"action": "status"}))
    assert status["active"] is True
    assert status["minutes_remaining"] >= 1


def test_study_guide_socratic_hint(world):
    session = XiaomanSession(id=world.user_id, user_id=world.user_id)
    tool = StudyGuideTool()
    raw = json.loads(
        tool(session, {"action": "guide", "subject": "数学", "question": "二次函数不会配顶点"})
    )
    assert raw["ok"] is True
    assert raw["mode"] == "socratic"
    assert raw["subject"] == "math"
    assert "hint" in raw
    assert "答案" not in raw["hint"]


def test_study_guide_refuses_direct_answer(world):
    session = XiaomanSession(id=world.user_id, user_id=world.user_id)
    tool = StudyGuideTool()
    raw = json.loads(
        tool(session, {"action": "guide", "question": "直接告诉我答案选C"})
    )
    assert raw["mode"] == "refuse_answer"


def test_emotional_diary_on_vent(world):
    world.update_from_message("烦死了今天数学考砸了", "别难过呀")
    today = date.today().isoformat()
    entries = world.l8_dialogue.get_diary(today)
    emotional = [e for e in entries if e.get("kind") == "emotional"]
    assert len(emotional) >= 1
