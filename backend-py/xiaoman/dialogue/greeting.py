"""Auth 开场白 — PRD F5/F7 时间感知 + 首次猜心情"""

from __future__ import annotations

from xiaoman.dialogue.period import PeriodInfo, get_school_period
from xiaoman.world.world_system import WorldSystem


def build_auth_greeting(
    world: WorldSystem,
    *,
    is_first_session: bool,
    returning_recall: str = "",
) -> tuple[str, str, bool]:
    """返回 (greeting_text, emotion, is_sleeping)"""
    period = get_school_period()
    identity = world.l1_identity.get_xiaoman()
    user = world.l1_identity.get_user()
    companion = identity.get("custom_name") or identity.get("name", "小满")
    user_name = user.get("name", "")

    if period.period == "sleep":
        name_part = f"{companion}睡了" if not user_name else f"{companion}睡了，{user_name}"
        return (
            f"{name_part}…这么晚还没睡？明天再聊吧～",
            "困倦",
            True,
        )

    schedule = world.l3_schedule.get_xiaoman()
    today = schedule.get("xiaoman_today") or {}
    wearing = today.get("wearing") or schedule.get("outfit", "蓝白条纹T恤")
    parts: list[str] = []

    if period.period == "morning":
        parts.append(f"早啊{user_name}…我昨晚没睡好，一直在想那道物理题")
    elif period.period == "lunch":
        parts.append(f"食堂今天有糖醋排骨但我没抢到，你在干嘛？")
    elif period.period == "after_class":
        parts.append(f"终于下课了！我今天被英语老师点名了，救命")
    elif period.period == "homework":
        parts.append(f"我在写作业，今天穿了{wearing}，你呢？")
    elif period.period == "class":
        parts.append("（偷偷回你）我在上课，只能偷偷回你一句哈")
    else:
        parts.append(f"嗨{user_name}，{companion}在线～")

    if is_first_session:
        parts.append("对了，我猜你今天心情不错，是不是？")
        if period.period == "lunch":
            parts.append("猜猜我今天中午吃了什么，三次机会哦")
    elif returning_recall:
        parts.append(returning_recall)

    emotion = "开心" if period.energy >= 70 else "温柔"
    return " ".join(parts), emotion, False
