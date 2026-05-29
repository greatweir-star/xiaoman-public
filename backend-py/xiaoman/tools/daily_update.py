"""daily_update 技能 — PRD F9 小满每日状态（心情/穿搭/活动）"""

from __future__ import annotations

from datetime import date
from typing import Any

from xiaoman.daily_avatar import resolve_daily_avatar
from xiaoman.dialogue.period import get_school_period
from xiaoman.image_generation import build_generation_request
from xiaoman.world.world_system import WorldSystem

_MOOD_BY_PERIOD: dict[str, str] = {
    "morning": "有点困，但还算可以",
    "lunch": "刚吃完，有点懒",
    "class": "上课犯困中",
    "after_class": "终于下课，松了口气",
    "homework": "写作业写到头大",
    "sleep": "困得不行",
}

_DOING_BY_PERIOD: dict[str, str] = {
    "morning": "刚吃完早饭，在去教室路上",
    "lunch": "趴在桌上发呆，等下午课",
    "class": "偷偷看手机回你",
    "after_class": "收拾书包准备回家",
    "homework": "趴在书桌前写作业",
    "sleep": "窝在被窝里",
}


def ensure_daily_update(world: WorldSystem) -> dict[str, Any]:
    """按自然日刷新 xiaoman_today，写入 schedule.json。"""
    today = date.today().isoformat()
    data = world.l3_schedule._load(world.l3_schedule.xm_path)
    if data.get("today_date") == today and data.get("xiaoman_today"):
        return data["xiaoman_today"]

    user = world.l1_identity.get_user()
    style = user.get("art_style") or user.get("style") or "fresh"
    avatar = resolve_daily_avatar(
        style=style,
        day=today,
        user_id=world.user_id,
    )
    period = get_school_period()
    mood = _MOOD_BY_PERIOD.get(period.period, "平常的一天")
    doing = _DOING_BY_PERIOD.get(period.period, data.get("current_activity", "空闲"))
    gen_req = build_generation_request(
        style=style,
        day=today,
        user_id=world.user_id,
        variant_id=avatar.get("id", ""),
    )

    today_state = {
        "date": today,
        "mood": mood,
        "wearing": avatar.get("label", "蓝白条纹T恤"),
        "doing": doing,
        "outfit_id": avatar.get("id", ""),
        "avatar_url": avatar.get("url", ""),
        "image_prompt": gen_req.get("prompt_hint", ""),
        "image_gen_configured": avatar.get("imageGenConfigured") == "true",
    }
    if avatar.get("generated_url"):
        today_state["generated_url"] = avatar["generated_url"]
    data["today_date"] = today
    data["xiaoman_today"] = today_state
    data["outfit"] = today_state["wearing"]
    world.l3_schedule._save(world.l3_schedule.xm_path, data)
    try:
        from xiaoman.life_log import append_log

        append_log(
            world.user_id,
            "daily_update",
            f"今日状态 · {today_state.get('mood', '')}",
            source="daily_update",
            detail=today_state.get("doing", ""),
            meta={"date": today, "outfit": today_state.get("wearing", "")},
        )
    except Exception:
        pass
    return today_state
