"""Chunk rows for conversation content — 直接移植 OpenRath chunk.py 核心设计"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ChunkKind(str, Enum):
    """OpenRath 的 ChunkKind，保持不变"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_RESULT = "tool_result"
    EMOTION_STATE = "emotion"        # 小满扩展：情感状态快照
    MEMORY_RECALL = "memory"         # 小满扩展：触发的记忆


@dataclass(frozen=True, slots=True)
class ChunkRow:
    """Immutable row in chronological order — OpenRath 设计，直接复用"""
    kind: ChunkKind
    payload: dict[str, Any]


# --- 辅助函数（直接翻译 OpenRath） ---

def user_text_chunk(text: str) -> ChunkRow:
    """User message row"""
    return ChunkRow(kind=ChunkKind.USER, payload={"content": text})


def system_text_chunk(text: str) -> ChunkRow:
    """System prompt row"""
    return ChunkRow(kind=ChunkKind.SYSTEM, payload={"content": text})


def assistant_turn_chunk(content: str | None = None, tool_calls: list[dict] | None = None) -> ChunkRow:
    """Assistant message row; tool_calls stored in OpenAI-style wire form"""
    return ChunkRow(
        kind=ChunkKind.ASSISTANT,
        payload={"content": content, "tool_calls": tool_calls or []},
    )


def tool_feedback_chunk(tool_call_id: str, name: str, body: str) -> ChunkRow:
    """Tool result chunk for replay into the chat transcript"""
    return ChunkRow(
        kind=ChunkKind.TOOL_RESULT,
        payload={"tool_call_id": tool_call_id, "name": name, "content": body},
    )


def emotion_state_chunk(emotion: str, reason: str) -> ChunkRow:
    """小满扩展：情感状态快照 chunk"""
    return ChunkRow(
        kind=ChunkKind.EMOTION_STATE,
        payload={"emotion": emotion, "reason": reason},
    )


def memory_recall_chunk(memory_id: str, content: str) -> ChunkRow:
    """小满扩展：记忆引用 chunk"""
    return ChunkRow(
        kind=ChunkKind.MEMORY_RECALL,
        payload={"memory_id": memory_id, "content": content},
    )


@dataclass(frozen=True, slots=True)
class ChunkTable:
    """Append-only chronological chunk list — OpenRath 设计，直接复用"""
    rows: tuple[ChunkRow, ...] = ()

    def extend(self, *additional: ChunkRow) -> ChunkTable:
        """返回新的 ChunkTable（immutable）"""
        return ChunkTable(rows=self.rows + tuple(additional))

    def to_llm_messages(self) -> list[dict[str, Any]]:
        """转换为 OpenAI 格式的 messages 列表"""
        messages = []
        for row in self.rows:
            if row.kind == ChunkKind.SYSTEM:
                messages.append({"role": "system", "content": row.payload.get("content", "")})
            elif row.kind == ChunkKind.USER:
                messages.append({"role": "user", "content": row.payload.get("content", "")})
            elif row.kind == ChunkKind.ASSISTANT:
                msg: dict[str, Any] = {"role": "assistant"}
                content = row.payload.get("content")
                if content:
                    msg["content"] = content
                tool_calls = row.payload.get("tool_calls")
                if tool_calls:
                    msg["tool_calls"] = tool_calls
                messages.append(msg)
            elif row.kind == ChunkKind.TOOL_RESULT:
                messages.append({
                    "role": "tool",
                    "tool_call_id": row.payload.get("tool_call_id", ""),
                    "name": row.payload.get("name", ""),
                    "content": row.payload.get("content", ""),
                })
            # EMOTION_STATE 和 MEMORY_RECALL 不发给 LLM，只用于内部追踪
        return messages
