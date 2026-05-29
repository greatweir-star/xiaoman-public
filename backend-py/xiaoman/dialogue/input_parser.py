"""Phase 1 输入解析 — 轻量关键词分类"""

from __future__ import annotations

import re
from dataclasses import dataclass


_EMOTION_MAP = {
    "开心": ["开心", "高兴", "哈哈", "太好了", "爽"],
    "难过": ["难过", "哭", "伤心", "郁闷", "emo"],
    "烦躁": ["烦", "好烦", "崩溃", "气死", "服了"],
    "焦虑": ["焦虑", "紧张", "压力", "慌", "怕"],
    "疲惫": ["累", "困", "睡", "疲惫", "没劲"],
}

_INTENT_HINTS = {
    "vent": ["烦死了", "好烦", "今天好烦", "好烦啊", "气死", "受不了", "吐槽", "崩溃"],
    "share": ["今天", "刚才", "刚刚", "我跟你说"],
    "seek_help": ["怎么办", "帮我", "不会", "题目"],
    "greeting": ["你好", "在吗", "早", "嗨"],
}


@dataclass
class ParsedInput:
    message_type: str
    intent: str
    emotion: str
    keywords: list[str]


def parse_user_input(text: str) -> ParsedInput:
    lowered = text.strip()
    emotion = "平静"
    for label, words in _EMOTION_MAP.items():
        if any(w in lowered for w in words):
            emotion = label
            break

    intent = "small_talk"
    for name, words in _INTENT_HINTS.items():
        if any(w in lowered for w in words):
            intent = name
            break

    msg_type = "chat"
    if intent == "greeting":
        msg_type = "greeting"
    elif emotion != "平静":
        msg_type = "emotion"
    elif intent == "seek_help":
        msg_type = "help"

    keywords = re.findall(r"[\u4e00-\u9fff]{2,4}", lowered)[:6]

    return ParsedInput(
        message_type=msg_type,
        intent=intent,
        emotion=emotion,
        keywords=keywords,
    )
