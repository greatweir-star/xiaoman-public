"""Schedule Remind Tool — PRD Life 技能：作业/考试提醒"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import date, datetime
from typing import Any

from xiaoman.session import XiaomanSession
from xiaoman.tool_registry import XiaomanTool


class ScheduleRemindTool(XiaomanTool):
    """查看或记录用户日程提醒（作业、考试、特殊日期）。"""

    _world_getter: Callable[[str], Any] | None = None

    @classmethod
    def bind_world(cls, getter: Callable[[str], Any]) -> None:
        cls._world_getter = getter

    @property
    def name(self) -> str:
        return "schedule_remind"

    @property
    def description(self) -> str:
        return (
            "查看或记录用户的作业/考试/日程提醒。"
            "action=list 列出待办；add_exam 添加考试；add_reminder 添加提醒事项。"
        )

    @property
    def parameters(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "add_exam", "add_reminder"],
                    "description": "list=查看提醒；add_exam=添加考试；add_reminder=添加提醒",
                },
                "title": {"type": "string", "description": "考试或提醒名称"},
                "date": {"type": "string", "description": "日期 YYYY-MM-DD，可选"},
                "note": {"type": "string", "description": "补充说明"},
            },
            "required": ["action"],
        }

    def __call__(self, session: XiaomanSession, arguments: Mapping[str, Any]) -> str:
        uid = session.user_id or session.id
        if not self._world_getter:
            return json.dumps({"ok": False, "message": "日程服务未就绪"}, ensure_ascii=False)

        getter = type(self)._world_getter
        world = getter(uid) if getter else None
        action = str(arguments.get("action") or "list").strip()
        sched = world.l3_schedule

        if action == "add_exam":
            title = (arguments.get("title") or "").strip()
            when = (arguments.get("date") or date.today().isoformat()).strip()
            if not title:
                return json.dumps({"ok": False, "message": "请提供考试名称"}, ensure_ascii=False)
            sched.add_user_exam(title, when)
            return json.dumps(
                {"ok": True, "message": f"已记下考试「{title}」({when})"},
                ensure_ascii=False,
            )

        if action == "add_reminder":
            title = (arguments.get("title") or arguments.get("note") or "").strip()
            when = (arguments.get("date") or "").strip()
            if not title:
                return json.dumps({"ok": False, "message": "请提供提醒内容"}, ensure_ascii=False)
            if when:
                sched.add_special_date(title, when)
            else:
                sched.add_pending_reminder(title)
            return json.dumps(
                {"ok": True, "message": f"已记下提醒：{title}"},
                ensure_ascii=False,
            )

        return json.dumps(_build_reminder_snapshot(world), ensure_ascii=False)


def _build_reminder_snapshot(world: Any) -> dict[str, Any]:
    """汇总可提醒事项，供工具与开场白复用。"""
    user_sched = world.l3_schedule.get_user()
    xm_sched = world.l3_schedule.get_xiaoman()
    today = date.today()
    items: list[dict[str, str]] = []

    hw = user_sched.get("homework_status")
    if hw and hw not in ("已完成", "无"):
        items.append({"kind": "homework", "text": f"作业状态：{hw}"})

    for exam in user_sched.get("upcoming_exams") or []:
        name = exam.get("name", "考试")
        when = exam.get("date", "")
        days = _days_until(when, today)
        if days is not None and days <= 14:
            items.append({"kind": "exam", "text": f"{name}（{when}，还有{days}天）"})

    for sp in user_sched.get("special_dates") or []:
        name = sp.get("name", "事项")
        when = sp.get("date", "")
        days = _days_until(when, today)
        if days is not None and 0 <= days <= 7:
            items.append({"kind": "special", "text": f"{name}（{when}，还有{days}天）"})

    for rem in user_sched.get("pending_reminders") or []:
        items.append({"kind": "reminder", "text": rem if isinstance(rem, str) else str(rem)})

    countdown = xm_sched.get("countdown") or {}
    if countdown.get("days_left", 0) in range(1, 8):
        items.append(
            {
                "kind": "countdown",
                "text": f"距离{countdown.get('event', '大事')}还有{countdown['days_left']}天",
            }
        )

    return {"ok": True, "items": items, "count": len(items)}


def _days_until(date_str: str, today: date) -> int | None:
    if not date_str:
        return None
    try:
        target = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        return (target - today).days
    except ValueError:
        return None
