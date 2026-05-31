"""记忆系统核心测试 — PRD memory-03 §10"""

import json
import os
import tempfile
import shutil

import pytest

from xiaoman.emotion.detector import EmotionDetector
from xiaoman.memory.store import MemoryStore
from xiaoman.memory.extractor import MemoryExtractor
from xiaoman.memory.markdown_loader import load_global_memory_snippets
from xiaoman.world.linkage_config import evaluate_triggers, load_linkage_definitions
from xiaoman.world.world_system import WorldSystem


@pytest.fixture
def tmp_data(monkeypatch):
    tmp = tempfile.mkdtemp()
    import xiaoman.memory.store as store_mod
    import xiaoman.memory.user_scope as scope_mod
    monkeypatch.setattr(store_mod, "DATA_DIR", tmp)
    monkeypatch.setattr(scope_mod, "DATA_DIR", tmp)
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def test_user_level_facts_persist(tmp_data):
    store = MemoryStore(data_dir=tmp_data)
    store.save_fact("user_a", "用户叫阿梨", "identity", "L1")
    store.save_fact("user_a", "用户喜欢鬼灭", "preference", "L7")
    facts = store.load_facts("user_a")
    assert len(facts) == 2
    assert facts[0]["category"] == "identity"


def test_save_fact_dedupes_duplicate_within_window(tmp_data):
    store = MemoryStore(data_dir=tmp_data)
    assert store.save_fact("user_a", "我叫仲其伟", "preference", "L7") is True
    assert store.save_fact("user_a", "我叫仲其伟", "preference", "L7") is False
    assert len(store.load_facts("user_a")) == 1


def test_cursor_per_session(tmp_data):
    store = MemoryStore(data_dir=tmp_data)
    store.save_cursor("user_a", "sess1", 5)
    store.save_cursor("user_a", "sess2", 10)
    assert store.load_cursor("user_a", "sess1") == 5
    assert store.load_cursor("user_a", "sess2") == 10


def test_emotion_detector_keywords():
    det = EmotionDetector()
    r = det.detect("我今天好难过，想哭")
    assert r.emotion == "难过"
    assert r.source == "keyword"


def test_linkage_yaml_loads():
    defs = load_linkage_definitions()
    names = {d.name for d in defs}
    assert "情绪急救" in names
    assert "秘密深化" in names


def test_emotional_first_aid_trigger(tmp_data, monkeypatch):
    config_dir = os.path.join(os.path.dirname(__file__), "..", "config", "linkages")
    defs = load_linkage_definitions(config_dir)
    aid = next(d for d in defs if d.name == "情绪急救")
    assert evaluate_triggers(aid, "我好难过啊", [], {"user_emotion": "难过", "hour": 22})


def test_linkage_prompt_hint():
    """联动引擎：难过 → 情绪急救 → prompt_hint"""
    from unittest.mock import MagicMock

    mock_world = MagicMock()
    mock_world.l5_emotion.get_user.return_value = {"current_emotion": "难过"}
    mock_world.l5_emotion.set_xiaoman_emotion = MagicMock()
    mock_world.l6_skills.add_xp.return_value = {"old_level": 1, "new_level": 1}

    from xiaoman.world.linkage_engine import LinkageEngine

    engine = LinkageEngine(mock_world)
    config_dir = os.path.join(os.path.dirname(__file__), "..", "config", "linkages")
    engine.definitions = load_linkage_definitions(config_dir)
    engine.evaluate("我好难过", [])
    assert engine.get_prompt_hints()
    assert "共情" in engine.get_prompt_hints()


def test_secret_vault_roundtrip():
    from xiaoman.security.secret_vault import SecretVault

    enc = SecretVault.encrypt("只告诉你", "user_x")
    assert SecretVault.decrypt(enc, "user_x") == "只告诉你"
    redacted = SecretVault.redact_for_display({"content_encrypted": enc}, "user_x", reveal=False)
    assert "加密" in redacted["content"]


def test_mutual_exclusion_detects_memory_update():
    msgs = [{"role": "assistant", "tool_calls": [{"function": {"name": "memory_update"}}]}]
    assert MemoryExtractor._main_agent_wrote_memory(msgs)


def test_ws_parse_skill_unlock():
    from xiaoman.ws_protocol import parse_skill_unlock, format_recall_prompt

    changes = [
        {"linkage": "情绪急救", "result": "共情"},
        {"linkage": "dialogue→level_up", "old_level": 2, "new_level": 3, "result": "升级"},
    ]
    unlock = parse_skill_unlock(changes)
    assert unlock == (2, 3, "升级")

    prompt = format_recall_prompt([{"fact": "用户叫阿梨"}, {"text": "喜欢猫"}])
    assert "阿梨" in prompt
    assert "【相关记忆】" in prompt


def test_time_service_special_dates():
    from xiaoman.time_service import TimeService

    ts = TimeService()
    alerts = ts.check_special_dates({
        "exams": [{"subject": "数学", "date": "2099-06-01"}],
    })
    assert isinstance(alerts, list)


def test_lt01_emotional_first_aid_keywords():
    config_dir = os.path.join(os.path.dirname(__file__), "..", "config", "linkages")
    defs = load_linkage_definitions(config_dir)
    aid = next(d for d in defs if d.name == "情绪急救")
    assert evaluate_triggers(aid, "我好难过", [], {"user_emotion": "难过", "hour": 22})


def test_lt03_secret_share():
    config_dir = os.path.join(os.path.dirname(__file__), "..", "config", "linkages")
    defs = load_linkage_definitions(config_dir)
    sec = next(d for d in defs if d.name == "秘密深化")
    assert evaluate_triggers(
        sec,
        "我告诉你一个秘密",
        [],
        {"user_emotion": "平静", "hour": 14},
    )


def test_revealed_social_level_gates_crush():
    from xiaoman.world.l4_social import SocialLayer

    layer = SocialLayer.__new__(SocialLayer)
    layer.xm_path = "/fake/xm.json"
    layer._load = lambda path: {
        "deskmate": {"name": "小明"},
        "family": [],
        "besties": [],
        "crush": {"name": "某人"},
    }
    low = layer.get_xiaoman_visible(relation_level=1)
    high = layer.get_xiaoman_visible(relation_level=4)
    assert "crush" not in low
    assert "crush" in high


def test_markdown_loader_empty(tmp_data, monkeypatch):
    import xiaoman.memory.markdown_loader as ml

    monkeypatch.setattr(ml, "DATA_DIR", tmp_data)
    assert load_global_memory_snippets() == "" or "【全局记忆】" in load_global_memory_snippets()


def test_lt03_secret_share_trigger():
    config_dir = os.path.join(os.path.dirname(__file__), "..", "config", "linkages")
    secret = next(d for d in load_linkage_definitions(config_dir) if d.name == "秘密深化")
    assert evaluate_triggers(
        secret,
        "我告诉你一个秘密，别跟别人说",
        [],
        {"user_emotion": "平静", "hour": 14},
    )


def test_lt04_secret_low_relation_records_only(tmp_path, monkeypatch):
    """关系 XP 不足时只记录秘密，不注入深度 prompt_hint"""
    from unittest.mock import MagicMock

    from xiaoman.world.linkage_engine import LinkageEngine

    monkeypatch.setattr("xiaoman.world.world_system.DATA_DIR", str(tmp_path))
    world = WorldSystem("lt04_user")
    world.l6_skills._save(world.l6_skills.xm_path, {"xp": 10, "unlocked": [], "learning": []})
    engine = LinkageEngine(world)
    config_dir = os.path.join(os.path.dirname(__file__), "..", "config", "linkages")
    engine.definitions = load_linkage_definitions(config_dir)
    results = engine.evaluate("我告诉你一个秘密", [])
    assert any(r.get("action") == "store_secret" for r in results)
    assert not engine.get_prompt_hints()


def test_lt06_birthday_surprise_trigger():
    config_dir = os.path.join(os.path.dirname(__file__), "..", "config", "linkages")
    surprise = next(d for d in load_linkage_definitions(config_dir) if d.name == "惊喜感动")
    assert evaluate_triggers(
        surprise,
        "你好",
        [],
        {"user_emotion": "开心", "hour": 10, "birthday_days_until": 2},
    )


def test_birthday_surprise_engine_prompt(tmp_path, monkeypatch):
    from datetime import date, timedelta

    from xiaoman.world.linkage_engine import LinkageEngine

    monkeypatch.setattr("xiaoman.world.world_system.DATA_DIR", str(tmp_path))
    world = WorldSystem("bday_user")
    bday = (date.today() + timedelta(days=2)).isoformat()
    sched = world.l3_schedule._load(world.l3_schedule.u_path)
    sched["birthday"] = bday
    world.l3_schedule._save(world.l3_schedule.u_path, sched)
    engine = LinkageEngine(world)
    config_dir = os.path.join(os.path.dirname(__file__), "..", "config", "linkages")
    engine.definitions = load_linkage_definitions(config_dir)
    engine.evaluate("早呀", [])
    assert engine.get_prompt_hints()
    assert "喜悦" in engine.get_prompt_hints() or "庆祝" in engine.get_prompt_hints()


def test_parse_facts_json():
    ext = MemoryExtractor(llm_client=None)
    content = '[{"content": "用户叫小明", "category": "identity", "layer": "L1"}]'
    facts = ext._parse_facts_json(content)
    assert len(facts) == 1
    assert facts[0]["content"] == "用户叫小明"


def test_extract_name_from_self_intro():
    from xiaoman.memory.user_name import extract_name_from_text, is_name_recall_query

    assert extract_name_from_text("我叫仲其伟") == "仲其伟"
    assert extract_name_from_text("用户叫阿梨") is None
    assert is_name_recall_query("你还记得我叫什么名字吗？")


def test_apply_facts_syncs_name_from_preference_layer():
    world = WorldSystem("user_name_test_apply_facts")
    from xiaoman.world.fact_router import apply_facts_to_world

    apply_facts_to_world(
        world,
        [{"content": "我叫仲其伟", "category": "preference", "layer": "L7"}],
    )
    assert world.l1_identity.get_user()["name"] == "仲其伟"


def test_resolve_user_name_from_memories_prefers_latest(tmp_data):
    from xiaoman.memory.user_name import resolve_user_name_from_memories

    store = MemoryStore(data_dir=tmp_data)
    store.save_fact("user_a", "我叫仲其伟", "preference", "L7")
    facts = store.load_facts("user_a")
    assert resolve_user_name_from_memories(facts) == "仲其伟"


def test_recall_for_name_includes_stored_fact(tmp_data, monkeypatch):
    from unittest.mock import MagicMock

    from xiaoman.memory.engine import MemoryEngine
    from xiaoman.memory.user_name import build_user_name_prompt_block

    store = MemoryStore(data_dir=tmp_data)
    store.save_fact("user_a", "我叫仲其伟", "identity", "L1")
    llm = MagicMock()
    engine = MemoryEngine(llm)
    engine.store = store
    hits = engine.recall_for_name("user_a", top_k=3)
    texts = " ".join((h.get("fact") or h.get("text") or "") for h in hits)
    assert "仲其伟" in texts
    block = build_user_name_prompt_block("仲其伟", is_name_query=True)
    assert "仲其伟" in block
    assert "阿梨" not in block or "不要编造" in block
