"""Memory Search — 混合语义搜索（LanceDB 向量 + 关键词 + 重排序）

超越 OpenClaw memory_search：
1. LanceDB 向量检索（持久化索引）
2. 混合搜索（向量 + 全文）
3. 多信号重排序
4. 结果多样化
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from xiaoman.llm_service import LLMClient
from xiaoman.memory.user_scope import organized_path
from xiaoman.memory.vector_store import VectorStore

logger = logging.getLogger(__name__)


class MemorySearch:
    """混合语义搜索 — 超越 OpenClaw"""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.vector_store = VectorStore(llm_client)

    def search(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        diversity: bool = True,
    ) -> list[dict[str, Any]]:
        """混合搜索：LanceDB 向量 + 关键词 + 重排序
        
        Args:
            top_k: 返回数量（默认 5）
            diversity: 是否去重相似结果
        """
        # 1. LanceDB 混合搜索（向量 + 全文）
        results = self.vector_store.hybrid_search(user_id, query, top_k=top_k * 2)
        
        if not results:
            results = self._keyword_search(user_id, query, top_k=top_k * 2)
        
        # 2. 重排序（综合多个信号）
        reranked = self._rerank(results, query)
        
        # 3. 多样化（可选）
        if diversity:
            reranked = self._diversify(reranked)
        
        return reranked[:top_k]

    def _keyword_search(self, user_id: str, query: str, top_k: int) -> list[dict[str, Any]]:
        """关键词搜索（Fallback）"""
        path = organized_path(user_id)
        if not os.path.exists(path):
            return []
        
        with open(path, "r", encoding="utf-8") as f:
            memories = json.load(f)
        
        if not memories:
            return []
        
        keywords = self._extract_keywords(query)
        
        scored = []
        for mem in memories:
            fact = mem.get("fact", "")
            score = self._match_score(fact, keywords)
            weight = mem.get("weight", 0.5)
            tier_bonus = 1.2 if mem.get("tier") == "long_term" else 1.0
            final_score = score * weight * tier_bonus
            scored.append({
                "id": mem.get("id", ""),
                "text": fact,
                "score": final_score,
                "weight": weight,
                "tier": mem.get("tier", "short_term"),
                "source": "keyword",
            })
        
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _rerank(self, results: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        """重排序 — 综合多个信号"""
        for r in results:
            # 信号1：基础分数
            base_score = r.get("score", 0)
            
            # 信号2：长期记忆加分
            tier_bonus = 1.3 if r.get("tier") == "long_term" else 1.0
            
            # 信号3：长度适中
            fact_len = len(r.get("text", ""))
            length_bonus = 1.0
            if fact_len < 10:
                length_bonus = 0.8
            elif fact_len > 200:
                length_bonus = 0.9
            
            r["final_score"] = base_score * tier_bonus * length_bonus
        
        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        return results

    def _diversify(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """结果多样化"""
        diversified = []
        
        for r in results:
            text = r.get("text", "")
            is_similar = False
            for selected in diversified:
                if self._text_similarity(text, selected.get("text", "")) > 0.6:
                    is_similar = True
                    break
            
            if not is_similar:
                diversified.append(r)
        
        return diversified

    def _text_similarity(self, a: str, b: str) -> float:
        """文本相似度"""
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)

    def _extract_keywords(self, query: str) -> list[str]:
        """提取关键词"""
        try:
            response = self.llm_client.complete([
                {"role": "system", "content": "提取关键实体和概念，每行一个。最多10个。"},
                {"role": "user", "content": f"查询：{query}\n\n提取关键词："},
            ])
            content = response["choices"][0]["message"].get("content", "")
            keywords = [line.strip("- ").strip() for line in content.split("\n") if line.strip()]
            return keywords[:10]
        except Exception as e:
            logger.warning("Keyword extraction failed: %s", e)
            return query.lower().split()[:10]

    def _match_score(self, text: str, keywords: list[str]) -> float:
        """关键词匹配分数"""
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        if not keywords:
            return 0.0
        return matches / len(keywords)
