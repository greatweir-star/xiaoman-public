"""XiaomanSession — 小满会话状态载体"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from xiaoman.chunk import ChunkTable, ChunkRow, ChunkKind


@dataclass
class XiaomanSession:
    """小满会话状态载体 — 参考 OpenRath Session 设计
    
    包含：
    - chunk_table: 有序语义 chunks（对话历史）
    - user_id: 用户 ID
    - emotion_state: 当前情感状态
    - active_memories: 本次对话激活的记忆
    - abilities_unlocked: 本次解锁的能力
    - user_profile_delta: 用户画像的本次更新
    - cumulative_usage: 累计 token 用量
    """
    
    id: str = field(default_factory=lambda: str(uuid4()))
    chunk_table: ChunkTable = field(default_factory=ChunkTable)
    user_id: str = ""
    emotion_state: str = "温柔"           # 当前情感状态
    active_memories: list[str] = field(default_factory=list)
    abilities_unlocked: list[str] = field(default_factory=list)
    user_profile_delta: dict[str, Any] = field(default_factory=dict)
    cumulative_usage: int = 0
    budget_total_tokens: int = 8192       # Token 预算上限
    budget_exceeded: bool = False         # 是否已超预算
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 小满专属状态
    xiaoman_mood: str = "平静"             # 小满自己的心情
    xiaoman_energy: int = 50               # 精力值 0-100
    xiaoman_period: str = ""               # 当前时段
    
    def append_chunk(self, chunk: ChunkRow) -> None:
        """追加 chunk（immutable，返回新 ChunkTable）"""
        self.chunk_table = self.chunk_table.extend(chunk)
        self.updated_at = datetime.now()
    
    def get_recent_messages(self, n: int = 10) -> list[dict[str, Any]]:
        """获取最近 N 条消息（转换为 LLM 格式）"""
        all_messages = self.chunk_table.to_llm_messages()
        return all_messages[-n:] if len(all_messages) > n else all_messages
    
    def add_usage(self, tokens: int) -> bool:
        """累加 token 用量，返回是否超出预算"""
        prev_total = self.cumulative_usage
        self.cumulative_usage += tokens
        
        # 预算检查：只在第一次超过时触发
        if self.cumulative_usage > self.budget_total_tokens and prev_total <= self.budget_total_tokens:
            self.budget_exceeded = True
            return True
        return False
    
    def to_dict(self) -> dict[str, Any]:
        """序列化为 dict（用于持久化）"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "emotion_state": self.emotion_state,
            "active_memories": self.active_memories,
            "abilities_unlocked": self.abilities_unlocked,
            "user_profile_delta": self.user_profile_delta,
            "cumulative_usage": self.cumulative_usage,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "xiaoman_mood": self.xiaoman_mood,
            "xiaoman_energy": self.xiaoman_energy,
            "xiaoman_period": self.xiaoman_period,
        }
