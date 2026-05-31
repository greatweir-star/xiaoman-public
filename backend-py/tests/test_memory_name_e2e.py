"""记忆名字召回端到端 — identity + recall + prompt block"""

from unittest.mock import MagicMock

from xiaoman.memory.engine import MemoryEngine
from xiaoman.memory.store import MemoryStore
from xiaoman.memory.user_name import build_user_name_prompt_block, is_name_recall_query
from xiaoman.world.fact_router import apply_facts_to_world
from xiaoman.world.world_system import WorldSystem


def test_name_recall_pipeline(tmp_path, monkeypatch):
    import xiaoman.world.world_system as ws_mod

    monkeypatch.setattr(ws_mod, "DATA_DIR", str(tmp_path))
    user_id = "name_e2e_user"
    store = MemoryStore(data_dir=str(tmp_path))
    store.save_fact(user_id, "我叫小雨", "identity", "L1")

    engine = MemoryEngine(MagicMock())
    engine.store = store

    display = engine.resolve_user_display_name(
        user_id,
        identity_name="",
        understanding_name="",
    )
    assert display == "小雨"

    assert is_name_recall_query("你还记得我叫什么吗")
    hits = engine.recall(user_id, "你还记得我叫什么吗", top_k=3)
    joined = " ".join((h.get("fact") or "") for h in hits)
    assert "小雨" in joined

    block = build_user_name_prompt_block(display, is_name_query=True)
    assert "小雨" in block
    assert "阿梨" not in block or "不要编造" in block


def test_apply_facts_syncs_l1_then_resolve(tmp_path, monkeypatch):
    import xiaoman.world.world_system as ws_mod

    monkeypatch.setattr(ws_mod, "DATA_DIR", str(tmp_path))
    world = WorldSystem("name_sync_user")
    apply_facts_to_world(
        world,
        [{"content": "我叫小明", "category": "identity", "layer": "L1"}],
    )
    assert world.l1_identity.get_user()["name"] == "小明"

    store = MemoryStore(data_dir=str(tmp_path))
    engine = MemoryEngine(MagicMock())
    engine.store = store
    name = engine.resolve_user_display_name(
        "name_sync_user",
        identity_name=world.l1_identity.get_user()["name"],
    )
    assert name == "小明"
