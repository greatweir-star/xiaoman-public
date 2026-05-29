"""Night Guard Tool — 深夜模式检查"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from xiaoman.night_mode import build_night_guard_prompt, is_night_hours
from xiaoman.session import XiaomanSession
from xiaoman.tool_registry import XiaomanTool


class NightGuardTool(XiaomanTool):
    """检查是否在深夜时段 — LLM 可调用"""

    @property
    def name(self) -> str:
        return "night_guard"

    @property
    def description(self) -> str:
        return "检查当前时间是否在深夜时段（23:00-06:00）。如果是，返回拒绝标志和提示语。"

    @property
    def parameters(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }

    def __call__(self, session: XiaomanSession, arguments: Mapping[str, Any]) -> str:
        if is_night_hours():
            return json.dumps({
                "is_night": True,
                "message": build_night_guard_prompt(),
            }, ensure_ascii=False)
        return json.dumps({"is_night": False})
