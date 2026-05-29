"""Focus Buddy Tool — PRD Life 技能：专注陪伴（番茄钟 MVP）"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Any

from xiaoman.session import XiaomanSession
from xiaoman.tool_registry import XiaomanTool

_DEFAULT_MINUTES = 25


class FocusBuddyTool(XiaomanTool):
    """开启/查询/结束专注陪伴时段。"""

    _world_getter: Callable[[str], Any] | None = None

    @classmethod
    def bind_world(cls, getter: Callable[[str], Any]) -> None:
        cls._world_getter = getter

    @property
    def name(self) -> str:
        return "focus_buddy"

    @property
    def description(self) -> str:
        return (
            "专注陪伴：用户要写作业/学习时调用。"
            "action=start 开始（默认25分钟）；status 查剩余；done 提前结束。"
        )

    @property
    def parameters(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "status", "done"],
                    "description": "start=开始专注；status=查进度；done=结束",
                },
                "minutes": {
                    "type": "integer",
                    "description": "专注时长（分钟），默认25",
                },
                "task": {
                    "type": "string",
                    "description": "正在做什么，如「写数学作业」",
                },
            },
            "required": ["action"],
        }

    def __call__(self, session: XiaomanSession, arguments: Mapping[str, Any]) -> str:
        uid = session.user_id or session.id
        if not self._world_getter:
            return json.dumps({"ok": False, "message": "专注服务未就绪"}, ensure_ascii=False)

        getter = type(self)._world_getter
        world = getter(uid) if getter else None
        action = str(arguments.get("action") or "status").strip()
        sched = world.l3_schedule

        if action == "done":
            sched.clear_focus_session()
            return json.dumps(
                {"ok": True, "message": "专注结束，休息一下～", "active": False},
                ensure_ascii=False,
            )

        if action == "start":
            minutes = int(arguments.get("minutes") or _DEFAULT_MINUTES)
            minutes = max(5, min(60, minutes))
            task = (arguments.get("task") or "学习").strip()
            ends_at = datetime.now() + timedelta(minutes=minutes)
            sched.set_focus_session(task=task, ends_at=ends_at.isoformat(), minutes=minutes)
            return json.dumps(
                {
                    "ok": True,
                    "active": True,
                    "task": task,
                    "minutes": minutes,
                    "ends_at": ends_at.isoformat(),
                    "message": f"好，我陪你{task}，{minutes}分钟后休息",
                },
                ensure_ascii=False,
            )

        # status
        focus = sched.get_focus_session()
        if not focus.get("active"):
            return json.dumps(
                {"ok": True, "active": False, "message": "当前没有进行中的专注"},
                ensure_ascii=False,
            )
        remaining = sched.focus_minutes_remaining()
        return json.dumps(
            {
                "ok": True,
                "active": True,
                "task": focus.get("task", ""),
                "minutes_remaining": remaining,
                "message": f"还在陪你看{focus.get('task', '学习')}，还剩约{remaining}分钟",
            },
            ensure_ascii=False,
        )
