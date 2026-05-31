"""世界模型核心测试 — 对照 xiaoman-world-V0.01 MVP"""

import os
import shutil

import pytest

from xiaoman.world.fact_router import apply_facts_to_world
from xiaoman.world.world_system import WorldSystem


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr("xiaoman.world.world_system.DATA_DIR", str(tmp_path))
    user_id = "world_test_user"
    w = WorldSystem(user_id)
    yield w
    user_dir = os.path.join(tmp_path, "users", user_id)
    if os.path.isdir(user_dir):
        shutil.rmtree(user_dir, ignore_errors=True)


def test_world_initializes_from_templates(world):
    xm = world.l1_identity.get_xiaoman()
    assert xm.get("name") == "小满"
    assert xm.get("id") == f"XIAOMAN-{world.user_id}"
    assert world.l5_emotion.get_xiaoman().get("current_emotion")


def test_life_context_includes_time_mode(world):
    ctx = world.get_life_context_for_prompt()
    assert "【时间】" in ctx
    assert "【此刻状态】" in ctx


def test_update_homework_and_weather(world):
    world.update_from_message("今天作业写完了，外面下雨", "辛苦了")
    assert world.l3_schedule.get_user().get("homework_status") == "已完成"
    assert "雨" in world.l2_living_env.get_xiaoman().get("current_weather", "")


def test_dialogue_context_after_chat(world):
    world.update_from_message("明天再告诉你吧，今天好烦", "好，我等你")
    ctx = world.get_dialogue_context_for_prompt()
    assert "【对话延续】" in ctx
    assert "约定" in ctx or "烦恼" in ctx


def test_fact_router_schedule(world):
    changes = apply_facts_to_world(
        world,
        [{"content": "用户下周有数学考试", "category": "schedule", "layer": "L3"}],
    )
    assert any(c.get("layer") == "L3" for c in changes)
    exams = world.l3_schedule.get_user().get("upcoming_exams") or []
    assert len(exams) >= 1


def test_grade_sync(world):
    world.l1_identity.set_user_grade(10)
    assert world.l1_identity.get_xiaoman().get("grade") == 10
    assert world.l1_identity.get_xiaoman().get("grade_name") == "高一"
