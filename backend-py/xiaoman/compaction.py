"""Session Compaction — 参考 OpenRath session/compress.py 设计

当 chunk_table 超过 max_messages 时，压缩旧消息为摘要，保留最近 keep_recent 条。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from xiaoman.chunk import ChunkKind, ChunkRow, ChunkTable
from xiaoman.llm_service import LLMClient

logger = logging.getLogger(__name__)


def compact_chunk_table(
    chunk_table: ChunkTable,
    llm_client: LLMClient,
    max_messages: int = 12,
    keep_recent: int = 4,
) -> ChunkTable:
    """压缩 chunk_table，返回新的 ChunkTable
    
    策略：
    1. 如果消息数 <= max_messages，不压缩
    2. 将超过的部分（去掉 keep_recent）发给 LLM 生成摘要
    3. 用 SYSTEM chunk 替换被压缩的部分
    4. 保留最近 keep_recent 条
    """
    messages = chunk_table.to_llm_messages()
    if len(messages) <= max_messages:
        return chunk_table
    
    # 需要压缩的部分（去掉最近 keep_recent 条）
    to_compress = messages[:-keep_recent]
    to_keep = messages[-keep_recent:]
    
    # 生成摘要
    summary_prompt = (
        "请用一句话总结以下对话的关键内容（用户提到的重要信息、情绪变化）：\n\n"
        + "\n".join(f"{'用户' if m['role'] == 'user' else '小满'}: {m.get('content', '')}" for m in to_compress)
    )
    
    try:
        response = llm_client.complete([
            {"role": "system", "content": "你是一个对话摘要助手。用一句话总结。"},
            {"role": "user", "content": summary_prompt},
        ])
        summary = response["choices"][0]["message"].get("content", "之前的对话")
    except Exception as e:
        logger.warning("Compaction summary failed: %s", e)
        summary = "之前的对话内容"
    
    # 构建新的 chunks：摘要 + 保留的最近消息
    new_rows: list[ChunkRow] = [
        ChunkRow(
            kind=ChunkKind.SYSTEM,
            payload={"content": f"【对话摘要】{summary}"},
        ),
    ]
    
    # 重新添加保留的消息为 chunks
    for msg in to_keep:
        if msg["role"] == "user":
            from xiaoman.chunk import user_text_chunk
            new_rows.append(user_text_chunk(msg["content"]))
        elif msg["role"] == "assistant":
            from xiaoman.chunk import assistant_turn_chunk
            new_rows.append(assistant_turn_chunk(content=msg.get("content")))
        elif msg["role"] == "tool":
            from xiaoman.chunk import tool_feedback_chunk
            new_rows.append(tool_feedback_chunk(
                tool_call_id=msg.get("tool_call_id", ""),
                name=msg.get("name", ""),
                body=msg.get("content", ""),
            ))
    
    return ChunkTable(rows=tuple(new_rows))
