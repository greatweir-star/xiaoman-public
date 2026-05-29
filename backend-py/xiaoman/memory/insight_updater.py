"""记忆 V0.2 — 情绪天气、成长节点（对话后轻量更新）"""

from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime
from typing import Any

from xiaoman.llm_service import LLMClient
from xiaoman.world.world_system import WorldSystem

logger = logging.getLogger(__name__)

GROWTH_HEURISTIC = re.compile(
    r"(进步|考好了|考了|名次|和好|第一次|突破|获奖|表扬|开心死了|月考)",
    re.I,
)

WEATHER_PROMPT = """根据本轮对话，更新用户的「情绪天气」JSON，只输出 JSON 对象：
{{"last_mood":"一句话概括近期情绪","trigger":"主要触发因素或空字符串","pattern_note":"若发现规律写一句，否则空"}}

用户说：{user}
小满回：{assistant}
当前情绪标签：{emotion}
"""

PATTERN_PROMPT = """从用户近期表达中提炼一条可复用的「情绪规律」（12–30字，第三人称描述用户）。
只输出这一句话，不要引号、不要 JSON；若没有明显规律，只输出空字符串。

用户说：{user}
小满回：{assistant}
"""


class InsightUpdater:
    """对话轮次后的画像洞察更新（非阻塞 LLM + 规则兜底）"""

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client

    def update_after_turn(
        self,
        world: WorldSystem,
        *,
        user_text: str,
        assistant_text: str = "",
        detected_emotion: str = "",
        message_count: int = 0,
    ) -> dict[str, Any]:
        profile = world.l7_profile
        changes: dict[str, Any] = {}

        if GROWTH_HEURISTIC.search(user_text):
            moment = self._heuristic_growth_moment(user_text)
            if moment and profile.add_growth_moment(moment):
                changes["growth_moment"] = moment

        weather = profile.update_emotional_weather_heuristic(
            user_text,
            detected_emotion or "平静",
        )
        changes["emotional_weather"] = weather

        if self.llm_client and self.llm_client.api_key:
            threading.Thread(
                target=self._llm_weather_async,
                args=(world, user_text, assistant_text, detected_emotion),
                daemon=True,
            ).start()
            if message_count > 0 and message_count % 5 == 0:
                threading.Thread(
                    target=self._llm_emotion_pattern_async,
                    args=(world, user_text, assistant_text),
                    daemon=True,
                ).start()

        return changes

    def _heuristic_growth_moment(self, user_text: str) -> str:
        snippet = user_text.strip()[:120]
        if len(snippet) < 4:
            return ""
        return snippet

    def _llm_weather_async(
        self,
        world: WorldSystem,
        user_text: str,
        assistant_text: str,
        emotion: str,
    ) -> None:
        prompt = WEATHER_PROMPT.format(
            user=user_text[:500],
            assistant=(assistant_text or "")[:500],
            emotion=emotion or "未知",
        )
        try:
            resp = self.llm_client.complete(
                [{"role": "user", "content": prompt}],
            )
            content = (
                resp.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if content.startswith("```"):
                content = re.sub(r"^```\w*\n?", "", content)
                content = re.sub(r"\n?```$", "", content)
            data = json.loads(content)
            if isinstance(data, dict):
                world.l7_profile.merge_emotional_weather_llm(data)
        except Exception:
            logger.debug(
                "LLM emotional weather skipped for %s",
                world.user_id,
                exc_info=True,
            )

    def _llm_emotion_pattern_async(
        self,
        world: WorldSystem,
        user_text: str,
        assistant_text: str,
    ) -> None:
        prompt = PATTERN_PROMPT.format(
            user=user_text[:500],
            assistant=(assistant_text or "")[:500],
        )
        try:
            resp = self.llm_client.complete(
                [{"role": "user", "content": prompt}],
            )
            content = (
                resp.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if content and len(content) >= 6:
                world.l7_profile.add_emotion_pattern(content[:120])
        except Exception:
            logger.debug(
                "LLM emotion pattern skipped for %s",
                world.user_id,
                exc_info=True,
            )
