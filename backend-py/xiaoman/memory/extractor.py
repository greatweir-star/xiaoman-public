"""Memory Extractor — 异步事实提取模块

Forked Agent 异步提取 + 用户级存储 + 提取完成回调（向量索引 / 世界模型）
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from datetime import datetime
from typing import Any, Callable

BATCH_EXTRACT = os.getenv("XIAOMAN_BATCH_EXTRACT", "").lower() in ("1", "true", "yes")

from xiaoman.llm_service import LLMClient
from xiaoman.memory.lineage import LineageTracker
from xiaoman.memory.store import MemoryStore
from xiaoman.session import XiaomanSession
from xiaoman.world.fact_router import apply_facts_to_world
from xiaoman.world.world_system import WorldSystem

logger = logging.getLogger(__name__)

OnExtractComplete = Callable[[str, list[dict[str, Any]]], None]

EXTRACTION_PROMPT = """从以下对话中提取关于用户的关键事实，只输出 JSON 数组，不要其他文字。

要求：
1. 只提取用户明确说过的事实，不推测
2. category 取：identity / preference / event / emotion / relation
3. layer 取：L1-L8 之一
4. 无新信息则输出 []

格式示例：
[
  {{"content": "用户叫阿梨", "category": "identity", "layer": "L1"}},
  {{"content": "用户喜欢鬼灭之刃", "category": "preference", "layer": "L7"}}
]

对话：
{conversation}"""


class MemoryExtractor:
    """Forked Agent 异步记忆提取器"""

    def __init__(
        self,
        llm_client: LLMClient,
        store: MemoryStore | None = None,
        on_complete: OnExtractComplete | None = None,
    ):
        self.llm_client = llm_client
        self.store = store or MemoryStore()
        self.on_complete = on_complete
        self._lock = threading.Lock()
        self._running = False
        self._pending: list[tuple[str, str, list[dict[str, Any]]]] = []
        self.lineage_trackers: dict[str, LineageTracker] = {}
        self._world_getter: Callable[[str], WorldSystem | None] | None = None

    def set_world_getter(self, getter: Callable[[str], WorldSystem | None]) -> None:
        self._world_getter = getter

    def extract(self, session: XiaomanSession) -> None:
        """触发记忆提取 — 非阻塞"""
        user_id = session.user_id or session.id
        messages = session.chunk_table.to_llm_messages()

        with self._lock:
            if self._running:
                item = (user_id, session.id, messages)
                if item not in self._pending:
                    self._pending.append(item)
                    logger.info("Extractor busy, stashed user=%s session=%s", user_id, session.id)
                return
            self._running = True

        thread = threading.Thread(
            target=self._do_extract,
            args=(user_id, session.id, messages),
            daemon=True,
        )
        thread.start()

    def _do_extract(self, user_id: str, session_id: str, messages: list[dict[str, Any]]) -> None:
        try:
            self.store.migrate_session_to_user(session_id, user_id)
            cursor = self.store.load_cursor(user_id, session_id)
            new_messages = messages[cursor:]
            if not new_messages:
                return

            if self._main_agent_wrote_memory(new_messages):
                logger.info(
                    "Skip extract: main agent used memory_update user=%s session=%s",
                    user_id,
                    session_id,
                )
                self.store.save_cursor(user_id, session_id, len(messages))
                return

            logger.info("Memory extraction user=%s session=%s new_msgs=%d", user_id, session_id, len(new_messages))
            conversation = "\n".join(
                f"{'用户' if m['role'] == 'user' else '小满'}: {m.get('content', '')}"
                for m in new_messages
            )
            prompt = EXTRACTION_PROMPT.format(conversation=conversation)

            all_facts: list[dict[str, Any]] = []
            for _ in range(3):
                response = self.llm_client.complete([
                    {"role": "system", "content": "你是记忆提取助手，只输出合法 JSON 数组。"},
                    {"role": "user", "content": prompt},
                ])
                content = response["choices"][0]["message"].get("content", "")
                facts = self._parse_facts_json(content)
                if facts:
                    all_facts.extend(facts)
                    break
                if "[]" in content or "无新信息" in content:
                    break

            if all_facts:
                self._save_facts(user_id, all_facts)
                if self._world_getter:
                    world = self._world_getter(user_id)
                    if world:
                        apply_facts_to_world(world, all_facts)
                if self.on_complete:
                    self.on_complete(user_id, all_facts)

            self.store.save_cursor(user_id, session_id, len(messages))

        except Exception:
            logger.exception("Memory extraction failed user=%s", user_id)
        finally:
            self._drain_pending()

    def _drain_pending(self) -> None:
        with self._lock:
            self._running = False
            if not self._pending:
                return
            user_id, session_id, messages = self._pending.pop(0)
            self._running = True
        thread = threading.Thread(
            target=self._do_extract,
            args=(user_id, session_id, messages),
            daemon=True,
        )
        thread.start()

    def _parse_facts_json(self, content: str) -> list[dict[str, Any]]:
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return [f for f in data if isinstance(f, dict) and (f.get("content") or f.get("fact"))]
        except json.JSONDecodeError:
            pass
        return self._parse_facts_legacy(content)

    @staticmethod
    def _main_agent_wrote_memory(messages: list[dict[str, Any]]) -> bool:
        """主 Agent 已调用 memory_update 则跳过后台提取"""
        for msg in messages:
            if msg.get("role") == "assistant":
                for tc in msg.get("tool_calls") or []:
                    fn = tc.get("function") or {}
                    if fn.get("name") == "memory_update":
                        return True
            if msg.get("role") == "tool" and msg.get("name") == "memory_update":
                return True
        return False

    def _parse_facts_legacy(self, content: str) -> list[dict[str, Any]]:
        facts = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                text = line[1:].strip()
                if text:
                    facts.append({"content": text, "category": "general", "layer": "L7"})
        return facts

    def _save_facts(self, user_id: str, facts: list[dict[str, Any]]) -> None:
        if user_id not in self.lineage_trackers:
            self.lineage_trackers[user_id] = LineageTracker(user_id)
        tracker = self.lineage_trackers[user_id]

        extract_node_id = tracker.add_node(
            content=f"提取了 {len(facts)} 条事实",
            node_type="extract",
            metadata={"timestamp": datetime.now().isoformat(), "fact_count": len(facts)},
        )

        for fact in facts:
            content = fact.get("content") or fact.get("fact", "")
            category = fact.get("category", "general")
            layer = fact.get("layer", "")
            self.store.save_fact(user_id, content, category, layer)
            tracker.add_node(
                content=content,
                node_type="fact",
                parent_ids=[extract_node_id],
                metadata={"source": "conversation_extraction", "category": category},
            )

        logger.info("Saved %d facts for user %s", len(facts), user_id)

    def batch_extract_for_date(self, user_id: str, date: str) -> list[dict[str, Any]]:
        """夜间批量：将当日 facts 合并为一次 LLM 调用（XIAOMAN_BATCH_EXTRACT=1）"""
        if not BATCH_EXTRACT or not self.llm_client:
            return []

        facts = self.store.load_facts_for_date(user_id, date)
        if len(facts) < 3:
            return []

        lines = []
        for f in facts:
            text = f.get("fact") or f.get("content", "")
            if text:
                lines.append(f"- {text}")
        if not lines:
            return []

        prompt = EXTRACTION_PROMPT.format(conversation="\n".join(lines[:40]))
        try:
            response = self.llm_client.complete([
                {"role": "system", "content": "你是记忆整理助手，只输出合法 JSON 数组。"},
                {"role": "user", "content": prompt},
            ])
            content = response["choices"][0]["message"].get("content", "")
            merged = self._parse_facts_json(content)
            if merged:
                logger.info("Batch extract %d facts for user %s on %s", len(merged), user_id, date)
            return merged
        except Exception:
            logger.exception("Batch extract failed for user %s", user_id)
            return []
