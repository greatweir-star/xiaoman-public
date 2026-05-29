"""Phase 5 后处理 — 蛐蛐注入、猜心情追加"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from xiaoman.dialogue.config import quqiu_enabled, quqiu_probability
from xiaoman.dialogue.input_parser import ParsedInput
from xiaoman.dialogue.period import INTERNAL_REPLY_STYLES, PeriodInfo

_QUQIU_POOL = [
    "她今天好像心情不错，我多聊两句",
    "又是数学，我上辈子是不是得罪了数学",
    "三点了他还在写作业，要不要提醒一下休息",
    "食堂的糖醋排骨又没抢到，到底谁抢到了啊？",
    "他今天打字变慢了，是不是有点烦？",
    "今天天气不错，心情也跟着好了一点",
]


@dataclass
class PostProcessResult:
    text: str
    quqiu_injected: bool = False


def _count_quqiu_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip().startswith("~>"))


def strip_leaked_strategy_labels(text: str) -> str:
    """移除 LLM 误复述的时段 reply_style 等内部策略标签。"""
    result = text
    for label in sorted(INTERNAL_REPLY_STYLES, key=len, reverse=True):
        if label in result:
            result = result.replace(label, "")
    result = re.sub(r"[ \t]{2,}", " ", result)
    result = re.sub(r"…\s*+", "…", result)
    return result.strip()


def apply_post_process(
    text: str,
    *,
    period: PeriodInfo,
    parsed: ParsedInput | None = None,
    inject_guess_mood: bool = False,
    guess_mood_text: str = "",
    force_quqiu: bool = False,
) -> PostProcessResult:
    result_text = text.strip()
    injected = False

    if period.in_class and not result_text.startswith("（"):
        result_text = f"（偷偷回你）{result_text}"

    skip_quqiu = parsed is not None and (
        parsed.message_type == "emotion" or parsed.intent == "vent"
    )
    existing = _count_quqiu_lines(result_text)
    should_quqiu = not skip_quqiu and (
        force_quqiu
        or (quqiu_enabled() and existing == 0 and random.random() < quqiu_probability())
    )
    if should_quqiu and existing < 2:
        quqiu = random.choice(_QUQIU_POOL)
        result_text = f"{result_text}\n~> {quqiu}"
        injected = True

    if inject_guess_mood and guess_mood_text and guess_mood_text not in result_text:
        result_text = f"{result_text}\n{guess_mood_text}"

    # 一轮最多两句蛐蛐
    lines = result_text.splitlines()
    quqiu_seen = 0
    kept: list[str] = []
    for line in lines:
        if line.strip().startswith("~>"):
            quqiu_seen += 1
            if quqiu_seen <= 2:
                kept.append(line)
        else:
            kept.append(line)
    result_text = "\n".join(kept).strip()

    # 去掉 LLM 可能误用的 blockquote
    result_text = re.sub(r"^>\s*", "~> ", result_text, flags=re.MULTILINE)

    result_text = strip_leaked_strategy_labels(result_text)

    return PostProcessResult(text=result_text, quqiu_injected=injected)
