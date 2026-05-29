"""Persistence — JSONL 格式持久化

JSONL 优势：
1. 追加写入，不需要读取整个文件
2. 每行一个 JSON 对象，便于流式处理
3. 崩溃后可以从中间恢复
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

from xiaoman.chunk import ChunkKind, ChunkRow, ChunkTable
from xiaoman.session import XiaomanSession

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


class SessionWriter:
    """Session JSONL 写入器 — 参考 OpenRath SessionWriter"""

    def __init__(self, session_id: str, user_id: str = ""):
        self.session_id = session_id
        self.user_id = user_id
        self.dir_path = os.path.join(DATA_DIR, "sessions_jsonl")
        self.file_path = os.path.join(self.dir_path, f"{session_id}.jsonl")
        self.closed = False
        _ensure_dir(self.file_path)

    def write_header(self) -> None:
        """写入会话头信息"""
        header = {
            "type": "header",
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": datetime.now().isoformat(),
        }
        self._append_line(header)

    def write_chunk(self, chunk: ChunkRow) -> None:
        """追加写入一个 chunk"""
        line = {
            "type": "chunk",
            "timestamp": datetime.now().isoformat(),
            "kind": chunk.kind.value,
            "payload": chunk.payload,
        }
        self._append_line(line)

    def write_trailer(self) -> None:
        """写入会话尾标记"""
        trailer = {
            "type": "trailer",
            "closed": True,
            "closed_at": datetime.now().isoformat(),
        }
        self._append_line(trailer)
        self.closed = True

    def _append_line(self, obj: dict[str, Any]) -> None:
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def load_session_from_jsonl(session_id: str) -> list[ChunkRow]:
    """从 JSONL 文件加载会话 chunks"""
    file_path = os.path.join(DATA_DIR, "sessions_jsonl", f"{session_id}.jsonl")
    if not os.path.exists(file_path):
        return []

    rows: list[ChunkRow] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("type") == "chunk":
                    rows.append(ChunkRow(
                        kind=ChunkKind(obj["kind"]),
                        payload=obj["payload"],
                    ))
            except (json.JSONDecodeError, ValueError):
                logger.warning("Invalid JSONL line: %s", line[:50])
                continue

    return rows


def save_session_json(session: XiaomanSession) -> None:
    """同时保存 JSON（全量快照）用于快速加载"""
    path = os.path.join(DATA_DIR, "sessions", f"{session.user_id or session.id}.json")
    _ensure_dir(path)

    data = {
        "session_id": session.id,
        "user_id": session.user_id,
        "emotion_state": session.emotion_state,
        "cumulative_usage": session.cumulative_usage,
        "budget_exceeded": session.budget_exceeded,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "messages": [
            {"kind": row.kind.value, "payload": row.payload}
            for row in session.chunk_table.rows
        ],
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_session_json(user_id: str) -> list[dict[str, Any]]:
    """从 JSON 文件加载会话"""
    path = os.path.join(DATA_DIR, "sessions", f"{user_id}.json")
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("messages", [])


def chunks_to_chat_messages(rows: list[ChunkRow]) -> list[dict[str, Any]]:
    """将 chunk 历史转为前端 ChatMessage 结构（用于 session_sync）。"""
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.kind == ChunkKind.USER:
            text = (row.payload.get("content") or "").strip()
            if text:
                out.append({"sender": "user", "text": text, "kind": "normal"})
        elif row.kind == ChunkKind.ASSISTANT:
            text = (row.payload.get("content") or "").strip()
            if text:
                out.append({"sender": "xiaoman", "text": text, "kind": "normal"})
    return out


def load_chat_messages_for_user(user_id: str) -> list[dict[str, Any]]:
    """加载用户可展示的聊天消息（优先 JSON 快照）。"""
    raw = load_session_json(user_id)
    if not raw:
        return []
    rows: list[ChunkRow] = []
    for h in raw:
        try:
            rows.append(ChunkRow(kind=ChunkKind(h["kind"]), payload=h["payload"]))
        except (ValueError, KeyError):
            continue
    return chunks_to_chat_messages(rows)
