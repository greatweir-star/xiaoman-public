"""PRD V0.01 缺口回归 — daily_update / 回访开场 / 边界 / 存在编号"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from xiaoman.dialogue.boundary import romance_boundary_hints
from xiaoman.dialogue.greeting import build_auth_greeting
from xiaoman.dialogue.period import PeriodInfo
from xiaoman.dialogue.recall_greeting import build_returning_recall_line
from xiaoman.world.l1_identity import companion_code_for_user
from xiaoman.tools.daily_update import ensure_daily_update


def test_companion_code_format():
    code = companion_code_for_user("user-abc")
    assert code.startswith("#XM")
    assert len(code) == 9


def test_returning_recall_prefers_last_topic():
    line = build_returning_recall_line(last_topic="数学考砸了")
    assert "数学考砸了" in line


def test_returning_recall_from_memory():
    line = build_returning_recall_line(
        memories=[{"fact": "用户怕英语老师"}],
    )
    assert "英语老师" in line


def test_returning_recall_with_name_only():
    line = build_returning_recall_line(user_name="小雨")
    assert "小雨" in line


def test_romance_boundary_for_male_only():
    assert romance_boundary_hints("我喜欢你", "male")
    assert not romance_boundary_hints("我喜欢你", "female")


def test_auth_greeting_includes_returning_recall(monkeypatch):
    import xiaoman.dialogue.greeting as greeting_mod

    world = MagicMock()
    world.l1_identity.get_xiaoman.return_value = {"name": "小满", "custom_name": "桃桃"}
    world.l1_identity.get_user.return_value = {"name": "小明"}
    world.l3_schedule.get_xiaoman.return_value = {
        "outfit": "校服",
        "xiaoman_today": {"wearing": "蓝白条纹T恤"},
    }
    monkeypatch.setattr(
        greeting_mod,
        "get_school_period",
        lambda dt=None: PeriodInfo(
            period="lunch",
            energy=70,
            reply_style="轻松",
            in_class=False,
        ),
    )
    text, _, sleeping = build_auth_greeting(
        world,
        is_first_session=False,
        returning_recall="对了，上次聊到「作业」，后来怎么样了？",
    )
    assert not sleeping
    assert "上次聊到" in text
    assert "作业" in text


def test_daily_update_writes_today_state(tmp_path, monkeypatch):
    import xiaoman.world.world_system as ws_mod

    monkeypatch.setattr(ws_mod, "DATA_DIR", str(tmp_path))
    from xiaoman.world.world_system import WorldSystem

    user_id = "test-daily-user"
    world = WorldSystem(user_id)
    state = ensure_daily_update(world)
    assert state.get("wearing")
    assert state.get("mood")
    loaded = world.l3_schedule.get_xiaoman()
    assert loaded.get("xiaoman_today", {}).get("wearing") == state["wearing"]
