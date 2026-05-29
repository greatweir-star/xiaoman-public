"""WebSocket 事件推送 — 统一协议（PRD memory-03 §9.2 扩展）"""

from __future__ import annotations

from typing import Any

from fastapi import WebSocket

from xiaoman.ws_protocol import format_recall_prompt, parse_skill_unlock

__all__ = [
    "format_recall_prompt",
    "parse_skill_unlock",
    "ws_send_typing",
    "ws_send_memory_recall",
    "ws_send_linkage",
    "ws_send_skill_unlocked",
    "emit_linkage_ws_events",
    "ws_send_stream_start",
    "ws_send_stream_delta",
    "ws_send_stream_end",
]


async def ws_send_typing(websocket: WebSocket, active: bool = True) -> None:
    await websocket.send_json({"type": "typing", "payload": {"active": active}})


async def ws_send_memory_recall(websocket: WebSocket, items: list[dict[str, Any]]) -> None:
    if not items:
        return
    await websocket.send_json({
        "type": "memory_recall",
        "payload": {
            "items": [
                {"text": (it.get("fact") or it.get("text") or "").strip(), "score": it.get("score")}
                for it in items
                if (it.get("fact") or it.get("text"))
            ],
        },
    })


async def ws_send_linkage(websocket: WebSocket, changes: list[dict[str, Any]]) -> None:
    if not changes:
        return
    await websocket.send_json({
        "type": "linkage_triggered",
        "payload": {"changes": changes},
    })


async def ws_send_skill_unlocked(
    websocket: WebSocket,
    old_level: int,
    new_level: int,
    message: str = "",
) -> None:
    await websocket.send_json({
        "type": "skill_unlocked",
        "payload": {
            "old_level": old_level,
            "new_level": new_level,
            "message": message or f"关系升级 L{old_level} → L{new_level}",
        },
    })


async def emit_linkage_ws_events(websocket: WebSocket, changes: list[dict[str, Any]]) -> None:
    await ws_send_linkage(websocket, changes)
    unlock = parse_skill_unlock(changes)
    if unlock:
        old_level, new_level, message = unlock
        await ws_send_skill_unlocked(websocket, old_level, new_level, message)


async def ws_send_stream_start(websocket: WebSocket, message_id: str) -> None:
    await websocket.send_json({
        "type": "stream_start",
        "payload": {"messageId": message_id, "sender": "xiaoman"},
    })


async def ws_send_stream_delta(
    websocket: WebSocket,
    message_id: str,
    delta: str,
) -> None:
    if not delta:
        return
    await websocket.send_json({
        "type": "stream_delta",
        "payload": {"messageId": message_id, "delta": delta},
    })


async def ws_send_stream_end(
    websocket: WebSocket,
    message_id: str,
    *,
    text: str,
    emotion: str,
    is_sleeping: bool = False,
    energy: int | None = None,
) -> None:
    payload: dict[str, Any] = {
        "messageId": message_id,
        "sender": "xiaoman",
        "text": text,
        "emotion": emotion,
        "isSleeping": is_sleeping,
    }
    if energy is not None:
        payload["energy"] = energy
    await websocket.send_json({
        "type": "stream_end",
        "payload": payload,
    })
