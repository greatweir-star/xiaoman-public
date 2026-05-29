"""Time Sense Tool — 使用 TimeService（PRD memory-03 §7.3）"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from xiaoman.session import XiaomanSession
from xiaoman.time_service import TimeService
from xiaoman.tool_registry import XiaomanTool


class TimeSenseTool(XiaomanTool):
    """获取当前时间感知 — LLM 可调用"""

    @property
    def name(self) -> str:
        return "time_sense"

    @property
    def description(self) -> str:
        return "获取当前时间信息（时段、日期、星期、特殊提醒），用于时间感知回复。"

    @property
    def parameters(self) -> Mapping[str, Any]:
        return {"type": "object", "properties": {}}

    def __call__(self, session: XiaomanSession, arguments: Mapping[str, Any]) -> str:
        ts = TimeService()
        ctx = ts.get_time_context()
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return (
            f"现在{ctx.day_type}{ctx.period}，"
            f"{ctx.hour}点，{weekdays[ctx.weekday]}，季节{ctx.season}。"
            f"小满状态：{ctx.xiaoman_status}。"
        )
