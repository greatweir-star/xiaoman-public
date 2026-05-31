#!/usr/bin/env py -3
"""记忆系统冒烟测试 — 不依赖 LLM"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import shutil

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from xiaoman.memory.store import MemoryStore
from xiaoman.memory.extractor import MemoryExtractor
from xiaoman.security.secret_vault import SecretVault
from xiaoman.world.linkage_config import load_linkage_definitions, evaluate_triggers


def main() -> int:
    tmp = tempfile.mkdtemp()
    import xiaoman.memory.store as sm
    import xiaoman.memory.user_scope as us

    sm.DATA_DIR = tmp
    us.DATA_DIR = tmp

    store = MemoryStore(data_dir=tmp)
    uid = "smoke_user"

    store.save_fact(uid, "用户叫测试", "identity", "L1")
    store.save_fact(uid, "用户喜欢猫", "preference", "L7")
    assert len(store.load_facts(uid)) == 2

    enc = SecretVault.encrypt("我的秘密", uid)
    assert SecretVault.decrypt(enc, uid) == "我的秘密"

    assert MemoryExtractor._main_agent_wrote_memory([
        {"role": "assistant", "tool_calls": [{"function": {"name": "memory_update"}}]},
    ])

    config_dir = os.path.join(ROOT, "config", "linkages")
    aid = next(d for d in load_linkage_definitions(config_dir) if d.name == "情绪急救")
    assert evaluate_triggers(aid, "我好难过", [], {"user_emotion": "难过", "hour": 22})

    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({"status": "ok", "checks": 4}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
