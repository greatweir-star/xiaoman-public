"""TC5 情绪承接 — 规则兜底（LLM 弱/失败时仍先接住情绪）"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xiaoman.dialogue.input_parser import ParsedInput

_NEGATIVE = frozenset({"难过", "烦躁", "焦虑", "疲惫", "愤怒", "生气"})

_VENT_FALLBACK_FEMALE = [
    "怎么啦？先跟我说说，我听着呢～",
    "抱抱你，今天发生啥了？",
    "听起来你今天不太顺，想吐槽就吐出来吧～",
]
_VENT_FALLBACK_MALE = [
    "怎么了？慢慢说，我听着。",
    "嗯，听起来挺烦的，发生啥了？",
    "先缓口气，愿意的话跟我说说？",
]
_SAD_FALLBACK = [
    "怎么啦…我在这儿呢。",
    "抱抱，愿意多说一点吗？",
]
_ANXIOUS_FALLBACK = [
    "听起来压力挺大的，先喘口气～",
    "别急，慢慢说，我陪你理一理。",
]


def needs_emotion_hold(
    parsed: "ParsedInput",
    *,
    detected_emotion: str = "",
) -> bool:
    if parsed.intent == "vent" or parsed.message_type == "emotion":
        return True
    em = parsed.emotion if parsed.emotion != "平静" else detected_emotion
    return em in _NEGATIVE


def emotion_hold_strategy_hint(user_gender: str) -> str:
    if user_gender == "male":
        return (
            "【情绪承接】先认可感受、问一句「怎么了」，不要列建议清单或说教"
        )
    return "【情绪承接】先抱住情绪（抱抱/怎么啦），别讲道理或急着给办法"


MIN_HOLD_REPLY_CHARS = 10


def should_apply_emotion_hold_fallback(
    clean_text: str,
    parsed: "ParsedInput",
    *,
    detected_emotion: str = "",
) -> bool:
    """流式/非流式：LLM 正文过短且需承接时，用规则模板替换 stream_end 正文。"""
    return (
        len((clean_text or "").strip()) < MIN_HOLD_REPLY_CHARS
        and needs_emotion_hold(parsed, detected_emotion=detected_emotion)
    )


def finalize_assistant_text(
    clean_text: str,
    user_text: str,
    parsed: "ParsedInput",
    *,
    user_gender: str = "female",
    user_name: str = "",
    detected_emotion: str = "",
) -> tuple[str, bool]:
    """返回 (正文, 是否使用了规则兜底)。"""
    if should_apply_emotion_hold_fallback(
        clean_text, parsed, detected_emotion=detected_emotion
    ):
        return (
            pick_emotion_hold_fallback(
                user_text,
                parsed,
                user_gender=user_gender,
                user_name=user_name,
                detected_emotion=detected_emotion,
            ),
            True,
        )
    return clean_text, False


def pick_emotion_hold_fallback(
    user_text: str,
    parsed: "ParsedInput",
    *,
    user_gender: str = "female",
    user_name: str = "",
    detected_emotion: str = "",
) -> str:
    """规则模板回复 — loop 失败或回复过短时使用。"""
    em = parsed.emotion if parsed.emotion != "平静" else detected_emotion
    pool = _VENT_FALLBACK_MALE if user_gender == "male" else _VENT_FALLBACK_FEMALE

    if parsed.intent == "vent" or any(w in user_text for w in ("烦", "气", "崩溃", "受不了")):
        line = random.choice(pool)
    elif em in ("难过",):
        line = random.choice(_SAD_FALLBACK)
    elif em in ("焦虑", "疲惫"):
        line = random.choice(_ANXIOUS_FALLBACK)
    else:
        line = random.choice(pool)

    name = (user_name or "").strip()
    if name and random.random() < 0.35:
        line = f"{name}，{line}"
    return line
