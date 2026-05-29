"""周/月报告生成 — 情绪数据可视化 + 小满寄语（PRD V0.03 Sprint 2）"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any

from xiaoman.life_timeline import list_events as timeline_list
from xiaoman.achievements import _load_achievements, ACHIEVEMENT_DEFS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

EMOTION_VALUES: dict[str, int] = {
    "开心": 20,
    "温柔": 10,
    "平静": 5,
    "无聊": -5,
    "累": -10,
    "烦": -20,
    "焦虑": -25,
    "难过": -30,
}

_KEYWORDS = ["考试", "作业", "朋友", "家人", "游戏", "学习", "累", "开心", "烦", "焦虑", "老师", "同学", "周末", "手机", "睡觉", "吃饭", "秘密", "吐槽"]


def _reports_dir(user_id: str) -> str:
    path = os.path.join(DATA_DIR, "users", user_id, "reports")
    os.makedirs(path, exist_ok=True)
    return path


def _weekly_report_path(user_id: str, monday: str) -> str:
    return os.path.join(_reports_dir(user_id), "weekly", f"{monday}.json")


def _monthly_report_path(user_id: str, month: str) -> str:
    return os.path.join(_reports_dir(user_id), "monthly", f"{month}.json")


def _get_monday(date: datetime) -> str:
    """获取 date 所在周的周一"""
    monday = date - timedelta(days=date.weekday())
    return monday.date().isoformat()


def _parse_date(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts).date().isoformat()
    except Exception:
        return ""


def _emotion_for_date(chat_events: list[dict[str, Any]], date_str: str) -> dict[str, Any] | None:
    """取某天的最后一次 chat 情绪"""
    day_events = [e for e in chat_events if _parse_date(e.get("ts", "")) == date_str]
    if not day_events:
        return None
    # 按时间排序，取最后一个
    day_events.sort(key=lambda e: e.get("ts", ""))
    emotion = day_events[-1].get("meta", {}).get("emotion", "平静")
    return {
        "date": date_str,
        "emotion": emotion,
        "value": EMOTION_VALUES.get(emotion, 0),
    }


def _build_emotion_trend(chat_events: list[dict[str, Any]], dates: list[str]) -> list[dict[str, Any] | None]:
    return [_emotion_for_date(chat_events, d) for d in dates]


def _top_emotions(chat_events: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    freq: dict[str, int] = {}
    for e in chat_events:
        emotion = e.get("meta", {}).get("emotion", "")
        if emotion:
            freq[emotion] = freq.get(emotion, 0) + 1
    return [{"label": k, "count": v} for k, v in sorted(freq.items(), key=lambda x: -x[1])[:limit]]


def _keyword_cloud(chat_events: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    freq: dict[str, int] = {}
    for e in chat_events:
        preview = e.get("title", "").split("·", 1)[1].strip() if "·" in e.get("title", "") else e.get("title", "")
        for kw in _KEYWORDS:
            if kw in preview:
                freq[kw] = freq.get(kw, 0) + 1
    return [{"word": k, "count": v} for k, v in sorted(freq.items(), key=lambda x: -x[1])[:limit]]


def _generate_xiaoman_note(
    dominant_emotion: str,
    chat_days: int,
    total_turns: int,
    period_days: int,
    top_emotions: list[dict[str, Any]],
) -> str:
    """基于规则生成小满寄语（50字以内）"""
    notes = {
        "开心": [
            "这周你心情不错呢，继续保持呀～",
            "看到你开心，我也跟着开心起来了！",
            "好事连连的一周，下周也要加油呀～",
        ],
        "温柔": [
            "这周我们聊得很温暖呢，谢谢你愿意分享～",
            "每次和你聊天都觉得很舒服，继续保持哦～",
        ],
        "平静": [
            "平平淡淡也是福，这周过得挺安稳的呢。",
            "生活有时候就是这样，平静中自有力量。",
        ],
        "累": [
            "这周辛苦了，记得好好休息呀。",
            "累了就停下来歇歇，我在这儿陪你。",
        ],
        "烦": [
            "这周烦心事不少吧？说出来会好受些。",
            "烦恼总会过去的，我陪你一起等天晴。",
        ],
        "焦虑": [
            "别太担心，事情没你想的那么糟。",
            "焦虑的时候深呼吸，我一直都在。",
        ],
        "难过": [
            "抱抱你，难过的时候我在。",
            "眼泪流出来就好了，我陪着你。",
        ],
    }
    import random
    candidates = notes.get(dominant_emotion, ["谢谢你这周愿意和我聊天，下周继续一起加油呀～"])
    base = random.choice(candidates)
    if chat_days >= period_days - 1 and total_turns > period_days * 3:
        base += " 这周聊得好多，超开心的！"
    elif chat_days <= 1:
        base += " 多来找我聊聊呀～"
    return base[:50]


def _ensure_llm_client() -> Any | None:
    """尝试初始化 LLMClient，失败返回 None"""
    try:
        from xiaoman.llm_service import LLMClient

        return LLMClient()
    except Exception:
        return None


def _generate_xiaoman_note_with_llm(
    llm_client: Any,
    dominant_emotion: str,
    chat_days: int,
    total_turns: int,
    period_days: int,
    top_emotions: list[dict[str, Any]],
) -> str:
    prompt = f"""你是小满，一个温暖的高中同桌AI。根据用户本周/月的情绪数据，写一句50字以内的贴心寄语。

情绪数据：
- 主导情绪：{dominant_emotion}
- 对话天数：{chat_days}/{period_days}天
- 对话轮次：{total_turns}
- 高频情绪：{", ".join(f"{e['label']}×{e['count']}" for e in top_emotions[:3])}

要求：
1. 语气像亲近的朋友
2. 50字以内
3. 不要说教
4. 根据主导情绪调整语气（开心就活泼，难过就温柔安慰）

请只输出寄语内容，不要加引号或其他说明。"""
    try:
        resp = llm_client.complete([{"role": "user", "content": prompt}])
        content = resp["choices"][0]["message"]["content"].strip().strip("\"").strip("'")
        return content[:50]
    except Exception:
        return ""


def generate_weekly_report(user_id: str, force: bool = False) -> dict[str, Any]:
    today = datetime.now()
    monday = _get_monday(today)
    path = _weekly_report_path(user_id, monday)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if not force and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if existing.get("start_date") == monday:
            return existing

    timeline = timeline_list(user_id, limit=500)
    chat_events = [e for e in timeline if e.get("type") == "chat"]

    # 最近7天日期
    dates = [(today - timedelta(days=i)).date().isoformat() for i in range(6, -1, -1)]
    emotion_trend = _build_emotion_trend(chat_events, dates)

    chat_dates = {_parse_date(e.get("ts", "")) for e in chat_events}
    chat_days = len([d for d in dates if d in chat_dates])
    total_turns = len(chat_events)

    top = _top_emotions(chat_events, limit=5)
    dominant = top[0]["label"] if top else "平静"

    llm_client = _ensure_llm_client()
    if llm_client:
        note = _generate_xiaoman_note_with_llm(
            llm_client, dominant, chat_days, total_turns, 7, top
        )
        if not note:
            note = _generate_xiaoman_note(dominant, chat_days, total_turns, 7, top)
    else:
        note = _generate_xiaoman_note(dominant, chat_days, total_turns, 7, top)

    report = {
        "period": "weekly",
        "start_date": dates[0],
        "end_date": dates[-1],
        "generated_at": datetime.now().isoformat(),
        "emotion_trend": emotion_trend,
        "top_emotions": top,
        "chat_days": chat_days,
        "total_chat_turns": total_turns,
        "xiaoman_note": note,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def generate_monthly_report(user_id: str, force: bool = False) -> dict[str, Any]:
    today = datetime.now()
    month = today.strftime("%Y-%m")
    path = _monthly_report_path(user_id, month)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if not force and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if existing.get("month") == month:
            return existing

    timeline = timeline_list(user_id, limit=2000)
    chat_events = [e for e in timeline if e.get("type") == "chat"]

    # 最近30天
    dates = [(today - timedelta(days=i)).date().isoformat() for i in range(29, -1, -1)]
    emotion_trend = _build_emotion_trend(chat_events, dates)

    chat_dates = {_parse_date(e.get("ts", "")) for e in chat_events}
    chat_days = len([d for d in dates if d in chat_dates])
    total_turns = len(chat_events)

    top = _top_emotions(chat_events, limit=5)
    dominant = top[0]["label"] if top else "平静"
    keywords = _keyword_cloud(chat_events, limit=8)

    # 成就解锁数
    ach_state = _load_achievements(user_id)
    this_month_start = month + "-01"
    next_month_year = today.year + (1 if today.month == 12 else 0)
    next_month_month = 1 if today.month == 12 else today.month + 1
    next_month_start = f"{next_month_year}-{next_month_month:02d}-01"
    unlocked_this_month = 0
    for aid, badge in ach_state.get("badges", {}).items():
        at = badge.get("unlocked_at", "")
        if this_month_start <= at < next_month_start:
            unlocked_this_month += 1

    # 关系等级变化
    from xiaoman.achievements import _get_current_level

    current_level = _get_current_level(user_id)
    level_change = {"from": ach_state.get("last_known_level", 1), "to": current_level}

    llm_client = _ensure_llm_client()
    if llm_client:
        note = _generate_xiaoman_note_with_llm(
            llm_client, dominant, chat_days, total_turns, 30, top
        )
        if not note:
            note = _generate_xiaoman_note(dominant, chat_days, total_turns, 30, top)
    else:
        note = _generate_xiaoman_note(dominant, chat_days, total_turns, 30, top)

    report = {
        "period": "monthly",
        "month": month,
        "generated_at": datetime.now().isoformat(),
        "emotion_trend": emotion_trend,
        "keyword_cloud": keywords,
        "achievements_unlocked": unlocked_this_month,
        "level_change": level_change,
        "chat_days": chat_days,
        "total_chat_turns": total_turns,
        "xiaoman_note": note,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def get_latest_weekly_report(user_id: str) -> dict[str, Any]:
    """获取最新周报告，不存在则生成"""
    return generate_weekly_report(user_id)


def get_latest_monthly_report(user_id: str) -> dict[str, Any]:
    """获取最新月报告，不存在则生成"""
    return generate_monthly_report(user_id)
