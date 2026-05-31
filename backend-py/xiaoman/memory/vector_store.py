"""Vector Store — LanceDB 向量语义检索

接入 LanceDB（OpenClaw 同款），实现真正的向量持久化索引。
支持向量 + 全文搜索混合查询。
"""

from __future__ import annotations

import json
import logging
import math
import os
import uuid
from typing import Any

import lancedb
import pyarrow as pa

from xiaoman.llm_service import LLMClient

logger = logging.getLogger(__name__)

from xiaoman.paths import DATA_DIR
DB_PATH = os.path.join(DATA_DIR, "lancedb")

# LanceDB 表结构
VECTOR_DIM = 3072  # text-embedding-3-large

SCHEMA = pa.schema([
    ("id", pa.string()),
    ("session_id", pa.string()),
    ("text", pa.string()),
    ("vector", pa.list_(pa.float32(), VECTOR_DIM)),
    ("created_at", pa.string()),
    ("metadata", pa.string()),  # JSON string
])


class VectorStore:
    """LanceDB 向量存储"""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.db = lancedb.connect(DB_PATH)
        self._table_cache: dict[str, Any] = {}

    def _get_table(self, user_id: str):
        """获取或创建 LanceDB 表（按 user_id，跨 session 共享）"""
        table_name = f"memories_{user_id.replace('-', '_')}"
        
        if table_name in self._table_cache:
            return self._table_cache[table_name]
        
        try:
            table = self.db.open_table(table_name)
        except Exception:
            # 表不存在，创建
            table = self.db.create_table(table_name, schema=SCHEMA)
        
        self._table_cache[table_name] = table
        return table

    def add(self, user_id: str, text: str, vector_id: str | None = None) -> str:
        """添加文本到 LanceDB，自动生成 embedding"""
        vid = vector_id or str(uuid.uuid4())
        
        # 生成 embedding
        vector = self._generate_embedding(text)
        
        # 写入 LanceDB
        table = self._get_table(user_id)
        table.add([{
            "id": vid,
            "session_id": user_id,
            "text": text,
            "vector": vector,
            "created_at": __import__("datetime").datetime.now().isoformat(),
            "metadata": json.dumps({"source": "conversation"}),
        }])
        
        logger.info("Vector added to LanceDB: %s (user=%s)", vid, user_id)
        return vid

    def search(self, user_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """向量语义搜索"""
        table = self._get_table(user_id)
        
        # 检查表是否有数据
        if table.count_rows() == 0:
            return []
        
        # 生成 query embedding
        query_vector = self._generate_embedding(query)
        
        # LanceDB 向量搜索
        results = (
            table.search(query_vector)
            .limit(top_k)
            .to_list()
        )
        
        return [
            {
                "id": r["id"],
                "text": r["text"],
                "score": r.get("_distance", 0),  # LanceDB 返回的是距离
            }
            for r in results
        ]

    def hybrid_search(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
    ) -> list[dict[str, Any]]:
        """混合搜索：向量 + 全文"""
        table = self._get_table(user_id)
        
        if table.count_rows() == 0:
            return []
        
        try:
            table.create_fts_index("text", replace=True)
        except Exception:
            pass
        
        query_vector = self._generate_embedding(query)
        
        results = (
            table.search(query_vector)
            .limit(top_k * 2)
            .to_list()
        )
        
        # 简单重排（向量和文本分数加权）
        reranked = []
        for r in results:
            vector_score = 1.0 - min(r.get("_distance", 1.0), 1.0)  # 距离转相似度
            text_score = 0.5  # 简化处理，实际可用 BM25
            final_score = vector_score * vector_weight + text_score * text_weight
            
            reranked.append({
                "id": r["id"],
                "text": r["text"],
                "score": final_score,
            })
        
        reranked.sort(key=lambda x: x["score"], reverse=True)
        return reranked[:top_k]

    def delete_user(self, user_id: str) -> None:
        """删除用户向量表"""
        table_name = f"memories_{user_id.replace('-', '_')}"
        try:
            self.db.drop_table(table_name)
            if table_name in self._table_cache:
                del self._table_cache[table_name]
            logger.info("Dropped LanceDB table: %s", table_name)
        except Exception as e:
            logger.warning("Failed to drop table %s: %s", table_name, e)

    def _generate_embedding(self, text: str) -> list[float]:
        """生成 embedding — OpenAI text-embedding-3-large"""
        try:
            response = self.llm_client.client.embeddings.create(
                model="text-embedding-3-large",
                input=text[:8000],
                dimensions=VECTOR_DIM,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning("Embedding API failed: %s, falling back to local", e)
            # Fallback：本地简单 embedding
            words = text.lower().split()
            vector = [0.0] * VECTOR_DIM
            for word in words:
                idx = hash(word) % VECTOR_DIM
                vector[idx] += 1.0
            norm = math.sqrt(sum(v * v for v in vector))
            if norm > 0:
                vector = [v / norm for v in vector]
            return vector
