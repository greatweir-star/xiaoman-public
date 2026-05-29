"""WebSocket 协议纯函数（无 FastAPI 依赖，便于单测）"""

from __future__ import annotations

import uuid
from typing import Any


def parse_skill_unlock(changes: list[dict[str, Any]]) -> tuple[int, int, str] | None:
    for change in changes:
        if change.get("linkage") != "dialogue→level_up":
            continue
        old_level = int(change.get("old_level", 1))
        new_level = int(change.get("new_level", old_level + 1))
        return old_level, new_level, change.get("result", "")
    return None


def format_recall_prompt(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return ""
    lines = "\n".join(
        f"- {(m.get('fact') or m.get('text') or '').strip()}"
        for m in memories
        if (m.get("fact") or m.get("text"))
    )
    return f"【相关记忆】\n{lines}\n\n" if lines else ""


def new_stream_message_id() -> str:
    return uuid.uuid4().hex[:16]


def extract_stream_delta(chunk: dict[str, Any]) -> str:
    """从 OpenAI 兼容 stream chunk 提取文本增量。"""
    choices = chunk.get("choices") or []
    if not choices:
        return ""
    delta = choices[0].get("delta") or {}
    return delta.get("content") or ""


def accumulate_stream_message(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """将 stream chunks 合并为 assistant message 结构。"""
    content_parts: list[str] = []
    tool_calls: dict[int, dict[str, Any]] = {}

    for chunk in chunks:
        choices = chunk.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        if piece := delta.get("content"):
            content_parts.append(piece)
        for tc in delta.get("tool_calls") or []:
            idx = int(tc.get("index", 0))
            slot = tool_calls.setdefault(
                idx,
                {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
            )
            if tc.get("id"):
                slot["id"] = tc["id"]
            fn = tc.get("function") or {}
            if fn.get("name"):
                slot["function"]["name"] += fn["name"]
            if fn.get("arguments"):
                slot["function"]["arguments"] += fn["arguments"]

    message: dict[str, Any] = {"role": "assistant"}
    full = "".join(content_parts)
    if full:
        message["content"] = full
    if tool_calls:
        message["tool_calls"] = [tool_calls[i] for i in sorted(tool_calls)]
    return message
