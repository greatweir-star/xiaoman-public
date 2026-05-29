"""三层情绪检测 — PRD memory-03 §7.1"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xiaoman.llm_service import LLMClient

logger = logging.getLogger(__name__)

EMOTIONS = ("开心", "平静", "疲惫", "焦虑", "难过", "愤怒")

KEYWORD_MAP: dict[str, list[str]] = {
    "开心": ["开心", "高兴", "棒", "耶", "哈哈", "太好了"],
    "疲惫": ["累", "困", "好累", "没精神"],
    "焦虑": ["焦虑", "紧张", "怕", "担心", "压力"],
    "难过": ["难过", "伤心", "哭", "失望", "郁闷"],
    "愤怒": ["生气", "愤怒", "气死", "烦死了"],
    "平静": [],
}

VENT_MARKERS = (
    "烦死了",
    "好烦",
    "今天好烦",
    "好烦啊",
    "受不了",
    "崩溃",
    "气死",
    "吐槽",
    "郁闷死了",
    "烦死了",
)


@dataclass
class EmotionResult:
    emotion: str
    confidence: float
    source: str  # keyword | rule | llm
    mixed: list[str] | None = None


class EmotionDetector:
    def __init__(self, llm_client: "LLMClient | None" = None):
        self.llm_client = llm_client

    @staticmethod
    def is_vent_message(text: str) -> bool:
        lowered = (text or "").strip()
        return any(m in lowered for m in VENT_MARKERS)

    def detect(self, text: str) -> EmotionResult:
        if self.is_vent_message(text):
            kw = self._detect_by_keywords(text)
            emotion = kw.emotion if kw and kw.emotion != "平静" else "烦躁"
            return EmotionResult(emotion, 0.88, "vent", kw.mixed if kw else None)

        result = self._detect_by_keywords(text)
        if result and result.confidence >= 0.75:
            return result

        result = self._detect_by_rules(text)
        if result and result.confidence >= 0.7:
            return result

        if self.llm_client:
            return self._detect_by_llm(text)
        return EmotionResult("平静", 0.5, "default")

    def _detect_by_keywords(self, text: str) -> EmotionResult | None:
        hits: list[str] = []
        for emotion, keywords in KEYWORD_MAP.items():
            if emotion == "平静":
                continue
            if any(kw in text for kw in keywords):
                hits.append(emotion)
        if not hits:
            return None
        primary = hits[0]
        mixed = hits[1:] if len(hits) > 1 else None
        return EmotionResult(primary, 0.85, "keyword", mixed)

    def _detect_by_rules(self, text: str) -> EmotionResult | None:
        if re.search(r"开心.+但.+累|高兴.+有点累", text):
            return EmotionResult("开心", 0.72, "rule", mixed=["疲惫"])
        if "又好又烦" in text or "开心又难过" in text:
            return EmotionResult("难过", 0.7, "rule", mixed=["开心"])
        if any(w in text for w in ["怎么办", "咋办", "好焦虑"]):
            return EmotionResult("焦虑", 0.68, "rule")
        return None

    def _detect_by_llm(self, text: str) -> EmotionResult:
        try:
            response = self.llm_client.complete([
                {"role": "system", "content": f"判断用户情绪，只回复一个词：{'/'.join(EMOTIONS)}"},
                {"role": "user", "content": text[:500]},
            ])
            content = response["choices"][0]["message"].get("content", "平静").strip()
            for em in EMOTIONS:
                if em in content:
                    return EmotionResult(em, 0.65, "llm")
        except Exception as e:
            logger.warning("LLM emotion detect failed: %s", e)
        return EmotionResult("平静", 0.5, "llm")
