"""Promotion Engine — 短期→长期记忆提升

核心概念：
- 短期记忆：刚提取的原始事实，容易遗忘
- 长期记忆：经过多次访问/重要性加权的记忆，持久保留
- 提升条件：访问次数、时间衰减、情感重要性

提升策略：
1. 访问频率：被多次访问的记忆→长期
2. 情感重要性：负面情绪/重要事件→优先保留
3. 时间衰减：长期未访问的→降级或清理
4. 重复确认：同一事实多次出现→提升置信度
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

from xiaoman.llm_service import LLMClient
from xiaoman.memory.user_scope import organized_path

logger = logging.getLogger(__name__)


class PromotionEngine:
    """记忆提升引擎 — 超越 OpenClaw 的 short-term promotion"""

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client

    def evaluate_and_promote(self, user_id: str) -> list[dict[str, Any]]:
        """评估并提升记忆
        
        返回被提升的记忆列表。
        """
        # 加载整理后的记忆
        path = organized_path(user_id)
        if not os.path.exists(path):
            return []
        
        with open(path, "r", encoding="utf-8") as f:
            memories = json.load(f)
        
        promoted = []
        for mem in memories:
            score = self._calculate_promotion_score(mem)
            
            if score >= 0.7:
                mem["tier"] = "long_term"
                mem["promotion_score"] = score
                promoted.append(mem)
                logger.info("Memory promoted to long-term: %s", mem.get("fact", "")[:50])
            else:
                mem["tier"] = "short_term"
                mem["promotion_score"] = score
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
        
        return promoted

    def _calculate_promotion_score(self, mem: dict[str, Any]) -> float:
        """计算提升分数 0-1 — 多维度评估 + LLM 辅助
        
        维度：
        1. 访问频率（0.2）— 被小满引用的次数
        2. 情感重要性（0.2）— 负面情绪/重要事件
        3. 时间衰减（0.15）— 越新越高
        4. 用户确认（0.2）— 用户是否确认过这个记忆
        5. LLM 评估（0.25）— LLM 判断这个记忆对用户的重要性
        """
        score = 0.0
        
        # 1. 访问频率（0.2）
        access_count = mem.get("access_count", 0)
        score += min(access_count / 5, 1.0) * 0.2
        
        # 2. 情感重要性（0.2）
        emotion = mem.get("emotion", "")
        emotion_scores = {
            "焦虑": 1.0, "难过": 0.9, "烦": 0.8, "累": 0.7,
            "开心": 0.6, "平静": 0.3, "温柔": 0.2,
        }
        score += emotion_scores.get(emotion, 0.3) * 0.2
        
        # 3. 时间衰减（0.15）
        timestamp_str = mem.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            age_days = (datetime.now() - timestamp).days
            time_score = max(0.2, 1.0 - age_days / 30)
            score += time_score * 0.15
        except (ValueError, TypeError):
            score += 0.05
        
        # 4. 用户确认（0.2）
        user_confirmed = mem.get("user_confirmed", False)
        score += (1.0 if user_confirmed else 0.0) * 0.2
        
        # 5. LLM 评估（0.25）
        if self.llm_client:
            llm_score = self._llm_evaluate_importance(mem)
            score += llm_score * 0.25
        else:
            score += 0.125  # 无 LLM 时取中值
        
        return min(score, 1.0)

    def _llm_evaluate_importance(self, mem: dict[str, Any]) -> float:
        """用 LLM 评估记忆的重要性 0-1"""
        fact = mem.get("fact", "")
        if not fact or len(fact) < 5:
            return 0.5
        
        try:
            response = self.llm_client.complete([
                {"role": "system", "content": "你是一个记忆重要性评估专家。评估这个事实对用户有多重要。只回复一个0-1之间的数字。"},
                {"role": "user", "content": f"事实：{fact}\n\n重要性评分（0-1）："},
            ])
            content = response["choices"][0]["message"].get("content", "0.5")
            # 提取数字
            import re
            match = re.search(r"(0\.\d+|1\.0|0|1)", content)
            if match:
                return float(match.group(1))
        except Exception as e:
            logger.warning("LLM importance evaluation failed: %s", e)
        
        return 0.5

    def cleanup_short_term(self, user_id: str, max_age_days: int = 14) -> int:
        path = organized_path(user_id)
        if not os.path.exists(path):
            return 0
        
        with open(path, "r", encoding="utf-8") as f:
            memories = json.load(f)
        
        now = datetime.now()
        kept = []
        removed = 0
        
        for mem in memories:
            tier = mem.get("tier", "short_term")
            timestamp_str = mem.get("timestamp", "")
            
            if tier == "short_term":
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    age_days = (now - timestamp).days
                    if age_days > max_age_days:
                        removed += 1
                        continue
                except (ValueError, TypeError):
                    pass
            
            kept.append(mem)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(kept, f, ensure_ascii=False, indent=2)
        
        logger.info("Cleaned up %d short-term memories for user %s", removed, user_id)
        return removed

    def demote_long_term(self, user_id: str, min_access_days: int = 90) -> int:
        path = organized_path(user_id)
        if not os.path.exists(path):
            return 0
        
        with open(path, "r", encoding="utf-8") as f:
            memories = json.load(f)
        
        now = datetime.now()
        demoted = 0
        
        for mem in memories:
            tier = mem.get("tier", "short_term")
            last_accessed = mem.get("last_accessed", "")
            
            if tier == "long_term" and last_accessed:
                try:
                    last_access = datetime.fromisoformat(last_accessed)
                    days_since_access = (now - last_access).days
                    if days_since_access > min_access_days:
                        mem["tier"] = "short_term"
                        mem["demotion_reason"] = f"{days_since_access}天未访问"
                        demoted += 1
                except (ValueError, TypeError):
                    pass
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
        
        logger.info("Demoted %d long-term memories for user %s", demoted, user_id)
        return demoted

    def get_long_term_memories(self, user_id: str) -> list[dict[str, Any]]:
        path = organized_path(user_id)
        if not os.path.exists(path):
            return []
        
        with open(path, "r", encoding="utf-8") as f:
            memories = json.load(f)
        
        return [m for m in memories if m.get("tier") == "long_term"]
