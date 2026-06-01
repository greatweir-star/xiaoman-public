"""Memory Engine — 小满记忆系统主入口（用户级）"""

from __future__ import annotations

import logging
from typing import Any, Callable

from xiaoman.llm_service import LLMClient
from xiaoman.memory.dreaming import DreamingEngine
from xiaoman.memory.extractor import MemoryExtractor
from xiaoman.memory.lineage import LineageTracker
from xiaoman.memory.promotion import PromotionEngine
from xiaoman.memory.search import MemorySearch
from xiaoman.memory.store import MemoryStore
from xiaoman.memory.user_name import collect_name_memory_snippets, is_name_recall_query
from xiaoman.memory.vector_store import VectorStore
from xiaoman.session import XiaomanSession
from xiaoman.world.world_system import WorldSystem

logger = logging.getLogger(__name__)


class MemoryEngine:
    """记忆引擎 — 统一入口"""

    def __init__(self, llm_client: LLMClient, *, memory_repository=None):
        self.llm_client = llm_client
        self.store = MemoryStore(fact_repository=memory_repository)
        self.search = MemorySearch(llm_client)
        self.dreaming = DreamingEngine(llm_client)
        self.promotion = PromotionEngine(llm_client)
        self.vector_store = VectorStore(llm_client)
        self.lineage: dict[str, LineageTracker] = {}
        self.extractor = MemoryExtractor(
            llm_client,
            store=self.store,
            on_complete=self._on_extract_complete,
        )

    def set_world_getter(self, getter: Callable[[str], WorldSystem | None]) -> None:
        self.extractor.set_world_getter(getter)

    def _on_extract_complete(self, user_id: str, facts: list[dict[str, Any]]) -> None:
        for fact in facts:
            text = fact.get("content") or fact.get("fact", "")
            if text:
                self.vector_store.add(user_id, text)

    def _uid(self, user_id: str | None, session: XiaomanSession | None = None) -> str:
        if user_id:
            return user_id
        if session and session.user_id:
            return session.user_id
        if session:
            return session.id
        raise ValueError("user_id required")

    def extract(self, session: XiaomanSession) -> None:
        if session.user_id:
            self.store.migrate_session_to_user(session.id, session.user_id)
        self.extractor.extract(session)

    def light_sleep(self, user_id: str) -> None:
        self.dreaming.run_light_sleep(user_id)

    def rem_sleep(self, user_id: str, date: str | None = None) -> str:
        return self.dreaming.run_rem_sleep(user_id, date)

    def run_full_dreaming(self, user_id: str) -> dict[str, Any]:
        return self.run_nightly_flow(user_id)

    def run_nightly_flow(self, user_id: str, world: WorldSystem | None = None) -> dict[str, Any]:
        """夜间整理流 — PRD memory-02 §4.3"""
        from datetime import datetime as dt
        import json
        import os

        date = dt.now().strftime("%Y-%m-%d")
        batch = self.extractor.batch_extract_for_date(user_id, date)
        if batch and world:
            from xiaoman.world.fact_router import apply_facts_to_world
            apply_facts_to_world(world, batch)

        self.light_sleep(user_id)
        promoted = self.promotion.evaluate_and_promote(user_id)
        demoted = self.promotion.demote_long_term(user_id)
        cleaned = self.promotion.cleanup_short_term(user_id)
        diary = self.rem_sleep(user_id)
        weekly_emotion = ""
        if world:
            weekly_emotion = self.dreaming.run_weekly_emotion_summary(user_id, world=world)

        indexed = 0
        for mem in self.get_organized(user_id):
            text = mem.get("fact") or mem.get("content", "")
            if text and mem.get("tier") == "long_term":
                self.vector_store.add(user_id, text)
                indexed += 1

        tomorrow_greeting = None
        if world:
            from xiaoman.time_service import TimeService
            alerts = TimeService().check_special_dates(world.l3_schedule.get_user())
            if alerts:
                tomorrow_greeting = f"明天要注意：{'；'.join(alerts)}"
                path = os.path.join(
                    os.path.dirname(__file__), "..", "data", "users", user_id, "xiaoman", "tomorrow_greeting.json"
                )
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"date": date, "greeting": tomorrow_greeting}, f, ensure_ascii=False)

        return {
            "status": "ok",
            "diary": diary,
            "weekly_emotion_summary": weekly_emotion,
            "promoted_count": len(promoted),
            "demoted_count": demoted,
            "cleaned_count": cleaned,
            "batch_extracted": len(batch),
            "vector_indexed": indexed,
            "tomorrow_greeting": tomorrow_greeting,
        }

    def recall(self, user_id: str, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if is_name_recall_query(query):
            return self.recall_for_name(user_id, top_k=top_k)
        results = self.search.search(user_id, query, top_k)
        for r in results:
            text = r.get("fact") or r.get("text", "")
            if text:
                self.store.bump_access(user_id, text)
        return results

    def recall_for_name(self, user_id: str, top_k: int = 5) -> list[dict[str, Any]]:
        """名字类问题：优先注入结构化名字事实，再补语义检索。"""
        facts = self.get_facts(user_id)
        organized = self.get_organized(user_id)
        long_term = self.get_long_term_memories(user_id)
        name_hits = collect_name_memory_snippets(facts, organized, long_term)
        seen_texts: set[str] = set()
        merged: list[dict[str, Any]] = []
        for mem in name_hits:
            text = (mem.get("fact") or mem.get("content") or mem.get("text") or "").strip()
            if text and text not in seen_texts:
                seen_texts.add(text)
                merged.append(mem)
        if len(merged) < top_k:
            for r in self.search.search(user_id, "用户名字 称呼 我叫", top_k=top_k):
                text = (r.get("fact") or r.get("text") or "").strip()
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    merged.append(r)
        for r in merged[:top_k]:
            text = r.get("fact") or r.get("text", "")
            if text:
                self.store.bump_access(user_id, text)
        return merged[:top_k]

    def resolve_user_display_name(
        self,
        user_id: str,
        *,
        identity_name: str = "",
        understanding_name: str = "",
    ) -> str:
        from xiaoman.memory.user_name import resolve_user_display_name

        return resolve_user_display_name(
            identity_name=identity_name,
            understanding_name=understanding_name,
            facts=self.get_facts(user_id),
            organized=self.get_organized(user_id),
            long_term=self.get_long_term_memories(user_id),
        )

    def recall_for_prompt(self, user_id: str, query: str) -> str:
        memories = self.recall(user_id, query, top_k=3)
        if not memories:
            return ""
        lines = "\n".join(f"- {m.get('fact') or m.get('text', '')}" for m in memories)
        return f"【相关记忆】\n{lines}\n\n"

    def save_fact(self, user_id: str, fact: str, category: str = "general", layer: str = "") -> bool:
        if not self.store.save_fact(user_id, fact, category, layer):
            return False
        self.vector_store.add(user_id, fact)
        return True

    def get_facts(self, user_id: str) -> list[dict[str, Any]]:
        return self.store.load_facts(user_id)

    def get_organized(self, user_id: str) -> list[dict[str, Any]]:
        return self.store.load_organized(user_id)

    def get_diary(self, user_id: str, date: str | None = None) -> list[dict[str, Any]]:
        return self.store.load_diary(user_id, date)

    def stats(self, user_id: str) -> dict[str, Any]:
        facts = self.get_facts(user_id)
        organized = self.get_organized(user_id)
        long_term = self.promotion.get_long_term_memories(user_id)
        return {
            "total_facts": len(facts),
            "total_organized": len(organized),
            "total_long_term": len(long_term),
            "last_updated": organized[-1].get("timestamp") if organized else None,
        }

    def _get_lineage(self, user_id: str) -> LineageTracker:
        if user_id not in self.lineage:
            self.lineage[user_id] = LineageTracker(user_id, self.store.data_dir)
        return self.lineage[user_id]

    def add_lineage_node(
        self,
        user_id: str,
        content: str,
        node_type: str,
        parent_ids: list[str] | None = None,
    ) -> str:
        return self._get_lineage(user_id).add_node(content, node_type, parent_ids)

    def trace_lineage(self, user_id: str, node_id: str) -> list[Any]:
        return self._get_lineage(user_id).trace(node_id)

    def get_lineage_summary(self, user_id: str, node_id: str) -> str:
        return self._get_lineage(user_id).get_lineage_summary(node_id)

    def promote_memories(self, user_id: str) -> list[dict[str, Any]]:
        return self.promotion.evaluate_and_promote(user_id)

    def cleanup_short_term(self, user_id: str, max_age_days: int = 7) -> int:
        return self.promotion.cleanup_short_term(user_id, max_age_days)

    def get_long_term_memories(self, user_id: str) -> list[dict[str, Any]]:
        return self.promotion.get_long_term_memories(user_id)

    def add_vector(self, user_id: str, text: str, vector_id: str | None = None) -> str:
        return self.vector_store.add(user_id, text, vector_id)

    def vector_search(self, user_id: str, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        return self.vector_store.search(user_id, query, top_k)
