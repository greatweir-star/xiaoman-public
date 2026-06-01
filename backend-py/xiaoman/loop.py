"""Session-first Loop — 参考 OpenRath session/loop.py 核心逻辑"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

from xiaoman.chunk import (
    ChunkRow,
    ChunkTable,
    assistant_turn_chunk,
    tool_feedback_chunk,
)
from xiaoman.session import XiaomanSession
from xiaoman.tool_registry import XiaomanTool, merge_tools, tools_to_schemas
from xiaoman.ws_protocol import accumulate_stream_message, extract_stream_delta

logger = logging.getLogger(__name__)


def _call_llm(
    llm_client,
    messages: list[dict[str, Any]],
    tool_schemas: list[dict[str, Any]],
    *,
    on_stream_delta: Callable[[str], None] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """调用 LLM；有 on_stream_delta 时用流式，且仅在无 tool_calls 时推送增量。"""
    tools_arg = tool_schemas if tool_schemas else None
    if not on_stream_delta:
        response = llm_client.complete(messages, tools=tools_arg)
        usage = response.get("usage")
        return response["choices"][0]["message"], usage

    chunks: list[dict[str, Any]] = []
    pending: list[str] = []
    for chunk in llm_client.complete_stream(messages, tools=tools_arg):
        chunks.append(chunk)
        if piece := extract_stream_delta(chunk):
            pending.append(piece)

    message = accumulate_stream_message(chunks)
    if not message.get("tool_calls"):
        for piece in pending:
            on_stream_delta(piece)

    usage = None
    if chunks:
        last = chunks[-1]
        usage = last.get("usage")
    return message, usage


def run_xiaoman_loop(
    session: XiaomanSession,
    system_prompt: str,
    tools: list[XiaomanTool],
    llm_client,
    max_tool_rounds: int = 8,
    on_stream_delta: Callable[[str], None] | None = None,
    on_usage: Callable[[dict[str, Any]], None] | None = None,
) -> XiaomanSession:
    """Session-first 执行循环 — 参考 OpenRath run_session_loop
    
    1. 组装 messages（system + chunk_table 历史）
    2. 调用 LLM
    3. 如有 tool_calls → dispatch tool → append result
    4. 继续 loop 直到没有 tool_calls 或达到 max_tool_rounds
    5. 返回更新后的 session
    """
    tool_table = merge_tools(tools)
    tool_schemas = tools_to_schemas(tool_table)
    
    for round_num in range(max_tool_rounds):
        # 1. 组装 messages
        messages = [
            {"role": "system", "content": system_prompt},
            *session.chunk_table.to_llm_messages(),
        ]
        
        # 2. 调用 LLM（最后一轮可流式；含 tool 的中间轮不推送增量）
        stream_cb = on_stream_delta if on_stream_delta else None
        started_at = time.perf_counter()
        try:
            assistant_message, usage = _call_llm(
                llm_client,
                messages,
                tool_schemas,
                on_stream_delta=stream_cb,
            )
        except Exception as exc:
            if on_usage:
                try:
                    on_usage(
                        {
                            "provider": getattr(llm_client, "provider", "openai-compatible"),
                            "model": getattr(llm_client, "model", "unknown"),
                            "request_type": "chat",
                            "usage": {},
                            "latency_ms": int((time.perf_counter() - started_at) * 1000),
                            "status": "error",
                            "metadata": {"error_type": type(exc).__name__},
                        }
                    )
                except Exception:
                    logger.exception("Failed to record LLM error usage")
            raise
        if on_usage:
            try:
                on_usage(
                    {
                        "provider": getattr(llm_client, "provider", "openai-compatible"),
                        "model": getattr(llm_client, "model", "unknown"),
                        "request_type": "chat",
                        "usage": usage or {},
                        "latency_ms": int((time.perf_counter() - started_at) * 1000),
                        "status": "success",
                    }
                )
            except Exception:
                logger.exception("Failed to record LLM usage")
        content = assistant_message.get("content")
        tool_calls = assistant_message.get("tool_calls")

        if usage:
            session.add_usage(usage.get("total_tokens", 0))

        # 4. 追加 assistant chunk
        session.append_chunk(
            assistant_turn_chunk(content=content, tool_calls=tool_calls)
        )
        
        # 5. 如果没有 tool_calls，结束循环
        if not tool_calls:
            break
        
        # 6. 执行 tools
        for tc in tool_calls:
            func = tc["function"]
            tool_name = func["name"]
            tool = tool_table.get(tool_name)
            
            if tool is None:
                logger.warning("Tool %s not found", tool_name)
                result = json.dumps({"error": f"Tool {tool_name} not found"})
            else:
                try:
                    arguments = json.loads(func["arguments"])
                    result = tool(session, arguments)
                except Exception as e:
                    logger.exception("Tool %s execution failed", tool_name)
                    result = json.dumps({"error": str(e)})
            
            # 追加 tool result chunk
            session.append_chunk(
                tool_feedback_chunk(
                    tool_call_id=tc["id"],
                    name=tool_name,
                    body=str(result),
                )
            )
    
    return session
