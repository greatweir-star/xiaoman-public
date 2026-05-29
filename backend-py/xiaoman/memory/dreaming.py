"""Dreaming Engine — 借鉴 OpenClaw memory-core 设计

自动整理记忆：
1. Light sleep（轻整理）：去重、合并相似记忆、更新权重
2. REM sleep（深度整理）：生成叙事报告（日记/周记）
3. 定时触发：每晚 23:00 自动执行
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any

from xiaoman.llm_service import LLMClient
from xiaoman.memory.user_scope import diary_path, facts_path, organized_path

logger = logging.getLogger(__name__)

FAST_DREAMING = os.getenv("XIAOMAN_DREAMING_FAST", "").lower() in ("1", "true", "yes")


class DreamingEngine:
    """记忆自整理引擎"""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def run_light_sleep(self, user_id: str) -> None:
        """Light sleep：轻整理 — 去重、合并、更新权重"""
        logger.info("Light sleep started for user %s", user_id)
        
        fpath = facts_path(user_id)
        if not os.path.exists(fpath):
            logger.info("No facts to process for user %s", user_id)
            return
        
        facts = self._load_facts(fpath)
        if not facts:
            return
        
        merged = self._deduplicate_facts(facts)
        weighted = self._update_weights(merged)
        self._save_organized_memory(user_id, weighted)
        logger.info("Light sleep completed: %d facts -> %d organized", len(facts), len(weighted))

    def run_rem_sleep(self, user_id: str, date: str | None = None) -> str:
        """REM sleep：深度整理 — 生成叙事报告（日记）"""
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        logger.info("REM sleep started for user %s, date %s", user_id, target_date)
        
        facts = self._load_facts_for_date(user_id, target_date)
        if not facts:
            logger.info("No facts for date %s", target_date)
            return ""
        
        # 生成叙事报告
        report = self._generate_narrative(facts, target_date)
        
        # 保存日记
        self._save_diary(user_id, target_date, report)
        logger.info("REM sleep completed: diary generated for %s", target_date)
        
        return report

    def _load_facts(self, path: str) -> list[dict[str, Any]]:
        """加载所有事实"""
        facts = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    facts.append(obj)
                except json.JSONDecodeError:
                    continue
        return facts

    def _load_facts_for_date(self, user_id: str, date: str) -> list[dict[str, Any]]:
        """加载指定日期的事实"""
        fpath = facts_path(user_id)
        if not os.path.exists(fpath):
            return []
        
        facts = []
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    timestamp = obj.get("timestamp", "")
                    if timestamp.startswith(date):
                        facts.append(obj)
                except json.JSONDecodeError:
                    continue
        return facts

    def _deduplicate_facts(self, facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """去重：LLM 辅助智能合并（超越简单 Jaccard）
        
        策略：
        1. 先用 Jaccard 粗筛（相似度 > 0.5）
        2. 对候选对用 LLM 判断是否同一事实
        3. 合并时保留更完整的版本
        """
        if not facts:
            return []
        
        merged = [facts[0]]
        
        for fact in facts[1:]:
            text = self._fact_text(fact)
            merged_with = None
            
            for i, existing in enumerate(merged):
                existing_text = self._fact_text(existing)
                sim = self._similarity(text, existing_text)
                if sim > 0.5:
                    if FAST_DREAMING or sim > 0.85 or self._llm_is_same_fact(text, existing_text):
                        merged_with = i
                        break
            
            if merged_with is not None:
                existing_text = self._fact_text(merged[merged_with])
                merged_text = self._llm_merge_facts(existing_text, text)
                merged[merged_with]["fact"] = merged_text
                merged[merged_with]["content"] = merged_text
                # 更新权重（取最大）
                merged[merged_with]["weight"] = max(
                    merged[merged_with].get("weight", 0.5),
                    fact.get("weight", 0.5)
                )
            else:
                merged.append(fact)
        
        return merged

    def _similarity(self, a: str, b: str) -> float:
        """简单相似度计算（Jaccard）"""
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)

    def _llm_is_same_fact(self, fact_a: str, fact_b: str) -> bool:
        """用 LLM 判断两个事实是否描述同一件事"""
        try:
            response = self.llm_client.complete([
                {"role": "system", "content": "判断以下两个事实是否描述同一件事。只回复'是'或'否'。"},
                {"role": "user", "content": f"事实A：{fact_a}\n事实B：{fact_b}\n\n是否同一件事？"},
            ])
            content = response["choices"][0]["message"].get("content", "否")
            return "是" in content
        except Exception as e:
            logger.warning("LLM same-fact check failed: %s", e)
            return False

    def _llm_merge_facts(self, fact_a: str, fact_b: str) -> str:
        """用 LLM 合并两个相似事实，保留完整信息"""
        try:
            response = self.llm_client.complete([
                {"role": "system", "content": "合并以下两个相似的事实，保留所有关键信息，去除重复。只输出合并后的事实。"},
                {"role": "user", "content": f"事实A：{fact_a}\n事实B：{fact_b}\n\n合并后："},
            ])
            merged = response["choices"][0]["message"].get("content", fact_a)
            return merged.strip() or fact_a
        except Exception as e:
            logger.warning("LLM merge facts failed: %s", e)
            return fact_a if len(fact_a) > len(fact_b) else fact_b

    def _update_weights(self, facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """更新权重：最近的事实权重更高"""
        now = datetime.now()
        for fact in facts:
            timestamp_str = fact.get("timestamp", "")
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                age_days = (now - timestamp).days
                # 最近1天权重1.0，每增加1天减0.1，最低0.3
                weight = max(0.3, 1.0 - age_days * 0.1)
                fact["weight"] = weight
            except (ValueError, TypeError):
                fact["weight"] = 0.5
        return facts

    @staticmethod
    def _fact_text(fact: dict[str, Any]) -> str:
        return fact.get("fact") or fact.get("content") or ""

    def _save_organized_memory(self, user_id: str, facts: list[dict[str, Any]]) -> None:
        path = organized_path(user_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(facts, f, ensure_ascii=False, indent=2)

    def _generate_narrative(self, facts: list[dict[str, Any]], date: str) -> str:
        """生成叙事报告 — 超越简单日记，支持多种叙事类型"""
        fact_texts = "\n".join(f"- {self._fact_text(f)}" for f in facts)
        
        # 判断叙事类型（基于事实数量和时间跨度）
        narrative_type = self._determine_narrative_type(facts)
        
        type_prompts = {
            "daily": "生成今天的日记，100-200字，包含心情、事件、感悟",
            "weekly": "生成本周总结，200-300字，包含本周 highlights、情绪变化、成长",
            "monthly": "生成本月回顾，300-500字，包含重要事件、情绪趋势、下月展望",
            "milestone": "生成重要节点记录，详细描述这个重要时刻",
        }
        
        prompt = f"""请根据以下事实，{type_prompts.get(narrative_type, type_prompts["daily"])}。

日期：{date}
事实：
{fact_texts}

要求：
1. 用第一人称"我"
2. 自然真实，像真正的朋友写的日记
3. 包含具体细节（时间、地点、人物）
4. 体现情绪变化和成长
5. 适当引用事实中的具体内容"""
        
        try:
            response = self.llm_client.complete([
                {"role": "system", "content": "你是一个日记生成专家，擅长写真实、有温度的日记。"},
                {"role": "user", "content": prompt},
            ])
            return response["choices"][0]["message"].get("content", "今天过得还行。")
        except Exception as e:
            logger.warning("Narrative generation failed: %s", e)
            return "今天过得还行。"

    def _determine_narrative_type(self, facts: list[dict[str, Any]]) -> str:
        """判断叙事类型"""
        if len(facts) >= 50:
            return "monthly"
        elif len(facts) >= 20:
            return "weekly"
        elif any("重要" in self._fact_text(f) or "第一次" in self._fact_text(f) for f in facts):
            return "milestone"
        return "daily"

    def run_weekly_emotion_summary(self, user_id: str, world: Any | None = None) -> str:
        """周情绪摘要 — 写入 user_understanding.emotion_patterns"""
        end = datetime.now()
        start = end - timedelta(days=7)
        facts: list[dict[str, Any]] = []
        fpath = facts_path(user_id)
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        ts = obj.get("timestamp", "")
                        if ts >= start.isoformat()[:10]:
                            if obj.get("category") == "emotion" or "情绪" in str(
                                obj.get("content", "")
                            ):
                                facts.append(obj)
                    except json.JSONDecodeError:
                        continue
        if not facts and world is None:
            return ""
        summary = ""
        if facts:
            fact_texts = "\n".join(f"- {self._fact_text(f)}" for f in facts[:30])
            prompt = f"""根据一周情绪相关事实，用一句话总结用户情绪规律（15-40字）：
{fact_texts}"""
            try:
                response = self.llm_client.complete(
                    [{"role": "user", "content": prompt}],
                )
                summary = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
            except Exception as e:
                logger.warning("Weekly emotion summary failed: %s", e)
        if not summary:
            summary = f"本周记录了 {len(facts)} 条情绪相关记忆"
        if world is not None:
            world.l7_profile.add_emotion_pattern(summary[:120])
        return summary

    def _save_diary(self, user_id: str, date: str, content: str) -> None:
        """保存日记"""
        path = diary_path(user_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        obj = {
            "date": date,
            "content": content,
            "created_at": datetime.now().isoformat(),
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
