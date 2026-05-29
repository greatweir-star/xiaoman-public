"""对话配置 — 读取 xiaoman.json"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def load_dialogue_config() -> dict[str, Any]:
    path = os.path.join(os.path.dirname(__file__), "..", "..", "xiaoman.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def night_mode_message() -> str:
    cfg = load_dialogue_config().get("nightMode", {})
    return cfg.get("message", "太晚啦，快去睡觉，明天再聊～")


def night_mode_enabled() -> bool:
    return load_dialogue_config().get("nightMode", {}).get("enabled", True)


def quqiu_enabled() -> bool:
    return load_dialogue_config().get("quqiu", {}).get("enabled", True)


def quqiu_probability() -> float:
    return float(load_dialogue_config().get("quqiu", {}).get("probability", 0.3))


def anti_addiction_config() -> dict[str, int | bool]:
    cfg = load_dialogue_config().get("antiAddiction", {})
    return {
        "enabled": bool(cfg.get("enabled", True)),
        "warn_minutes": int(cfg.get("warnMinutes", 30)),
        "warn_rounds": int(cfg.get("warnRounds", 15)),
    }
