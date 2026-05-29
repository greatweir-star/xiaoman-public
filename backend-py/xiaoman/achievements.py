"""成就系统 — 游戏化里程碑解锁（PRD V0.03 Sprint 2）"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any

from xiaoman.life_timeline import list_events as timeline_list

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

ACHIEVEMENT_DEFS: dict[str, dict[str, Any]] = {
    "first_vent": {
        "name": "第一次倾诉",
        "description": "累计检测到 1 次负面情绪关键词",
        "level": "bronze",
    },
    "secret_guardian": {
        "name": "秘密守护者",
        "description": "首次分享秘密（检测到\"秘密\"\"不告诉别人\"等关键词）",
        "level": "silver",
    },
    "companion_7d": {
        "name": "风雨同舟",
        "description": "连续 7 天有对话记录",
        "level": "silver",
    },
    "exam_buddy": {
        "name": "考试战友",
        "description": "考前 7 天内收到小满主动鼓励",
        "level": "bronze",
    },
    "emotion_stable": {
        "name": "情绪稳定",
        "description": "连续 3 次对话情绪值 > +10",
        "level": "gold",
    },
    "growth_witness": {
        "name": "成长见证",
        "description": "关系等级提升",
        "level": "gold",
    },
}

_NEGATIVE_KEYWORDS = ["难过", "伤心", "哭", "失望", "烦", "焦虑", "紧张", "压力", "郁闷", "累", "困", "疲惫", "讨厌", "郁闷"]
_SECRET_KEYWORDS = ["秘密", "不告诉别人", "别告诉别人", "不要说", "保密", "别讲出去", "不能让别人知道"]
_POSITIVE_EMOTIONS = {"开心", "温柔"}


def _achievements_path(user_id: str) -> str:
    path = os.path.join(DATA_DIR, "users", user_id)
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, "achievements.json")


def _load_achievements(user_id: str) -> dict[str, Any]:
    path = _achievements_path(user_id)
    if not os.path.exists(path):
        return {"unlocked": [], "badges": {}, "last_known_level": 1}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_achievements(user_id: str, data: dict[str, Any]):
    path = _achievements_path(user_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _user_emotions_path(user_id: str) -> str:
    return os.path.join(DATA_DIR, "users", user_id, "user", "emotions.json")


def _user_skills_path(user_id: str) -> str:
    return os.path.join(DATA_DIR, "users", user_id, "xiaoman", "skills.json")


def _extract_preview_from_chat_title(title: str) -> str:
    """从 '聊天 · preview' 中提取 preview"""
    if "·" in title:
        return title.split("·", 1)[1].strip()
    return title


def _check_first_vent(timeline: list[dict[str, Any]]) -> bool:
    for entry in timeline:
        if entry.get("type") != "chat":
            continue
        preview = _extract_preview_from_chat_title(entry.get("title", ""))
        if any(kw in preview for kw in _NEGATIVE_KEYWORDS):
            return True
    return False


def _check_secret_guardian(timeline: list[dict[str, Any]]) -> bool:
    for entry in timeline:
        if entry.get("type") != "chat":
            continue
        preview = _extract_preview_from_chat_title(entry.get("title", ""))
        if any(kw in preview for kw in _SECRET_KEYWORDS):
            return True
    return False


def _check_companion_7d(timeline: list[dict[str, Any]]) -> bool:
    chat_dates: set[str] = set()
    for entry in timeline:
        if entry.get("type") == "chat":
            ts = entry.get("ts", "")
            if ts:
                try:
                    d = datetime.fromisoformat(ts).date().isoformat()
                    chat_dates.add(d)
                except Exception:
                    pass
    if len(chat_dates) < 7:
        return False
    sorted_dates = sorted(chat_dates)
    max_streak = 1
    streak = 1
    for i in range(1, len(sorted_dates)):
        prev = datetime.fromisoformat(sorted_dates[i - 1]).date()
        cur = datetime.fromisoformat(sorted_dates[i]).date()
        if (cur - prev).days == 1:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 1
    return max_streak >= 7


def _check_exam_buddy(timeline: list[dict[str, Any]]) -> bool:
    for entry in timeline:
        if entry.get("type") != "linkage":
            continue
        title = entry.get("title", "")
        if any(kw in title for kw in ["考试", "鼓励", "考前", "加油"]):
            return True
    return False


def _check_emotion_stable(timeline: list[dict[str, Any]]) -> bool:
    """从 timeline chat 事件的 meta.emotion 中检查连续 3 次正面情绪"""
    emotions: list[str] = []
    for entry in reversed(timeline):
        if entry.get("type") != "chat":
            continue
        emotion = entry.get("meta", {}).get("emotion", "")
        if emotion:
            emotions.append(emotion)
        if len(emotions) >= 3:
            break
    if len(emotions) < 3:
        return False
    return all(e in _POSITIVE_EMOTIONS for e in emotions[:3])


def _get_current_level(user_id: str) -> int:
    path = _user_skills_path(user_id)
    if not os.path.exists(path):
        return 1
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        xp = data.get("xp", 0)
        thresholds = [0, 20, 50, 100, 200]
        level = 1
        for i, t in enumerate(thresholds):
            if xp >= t:
                level = i + 1
        return level
    except Exception:
        return 1


def _check_growth_witness(user_id: str, state: dict[str, Any]) -> bool:
    current = _get_current_level(user_id)
    last_known = state.get("last_known_level", 1)
    return current > last_known


def check_achievements(user_id: str) -> list[dict[str, Any]]:
    """检查并返回本次新增解锁的成就列表"""
    state = _load_achievements(user_id)
    unlocked = set(state.get("unlocked", []))
    timeline = timeline_list(user_id, limit=500)
    newly_unlocked: list[dict[str, Any]] = []

    checks = {
        "first_vent": lambda: _check_first_vent(timeline),
        "secret_guardian": lambda: _check_secret_guardian(timeline),
        "companion_7d": lambda: _check_companion_7d(timeline),
        "exam_buddy": lambda: _check_exam_buddy(timeline),
        "emotion_stable": lambda: _check_emotion_stable(timeline),
        "growth_witness": lambda: _check_growth_witness(user_id, state),
    }

    now = datetime.now().isoformat()
    for aid, check_fn in checks.items():
        if aid in unlocked:
            continue
        try:
            if check_fn():
                unlocked.add(aid)
                state.setdefault("badges", {})[aid] = {
                    "unlocked_at": now,
                    "level": ACHIEVEMENT_DEFS[aid]["level"],
                }
                newly_unlocked.append({
                    "id": aid,
                    "name": ACHIEVEMENT_DEFS[aid]["name"],
                    "level": ACHIEVEMENT_DEFS[aid]["level"],
                })
        except Exception:
            pass

    # 更新 last_known_level
    current_level = _get_current_level(user_id)
    state["last_known_level"] = current_level
    state["unlocked"] = list(unlocked)
    _save_achievements(user_id, state)
    return newly_unlocked


def get_achievements_state(user_id: str) -> dict[str, Any]:
    """返回完整成就状态（含未解锁的占位）"""
    state = _load_achievements(user_id)
    badges = state.get("badges", {})
    result = []
    for aid, info in ACHIEVEMENT_DEFS.items():
        badge = badges.get(aid)
        result.append({
            "id": aid,
            "name": info["name"],
            "description": info["description"],
            "level": info["level"],
            "unlocked": aid in state.get("unlocked", []),
            "unlocked_at": badge.get("unlocked_at") if badge else None,
        })
    return {"achievements": result, "total": len(ACHIEVEMENT_DEFS), "unlocked_count": len(state.get("unlocked", []))}
