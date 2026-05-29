"""会话上下文辅助 — 轮次 / 摘要 / 话题 / 连续低情绪"""

from __future__ import annotations

from xiaoman.chunk import ChunkKind, ChunkTable


_NEGATIVE = frozenset({"累", "烦", "难过", "焦虑", "压力", "疲惫", "郁闷", "无聊"})


def count_user_turns(chunk_table: ChunkTable) -> int:
    return sum(1 for r in chunk_table.rows if r.kind == ChunkKind.USER)


def extract_session_summary(chunk_table: ChunkTable) -> str:
    for row in chunk_table.rows:
        if row.kind == ChunkKind.SYSTEM:
            content = row.payload.get("content", "")
            if "【对话摘要】" in content:
                return content.replace("【对话摘要】", "").strip()
    return ""


def extract_last_topic(chunk_table: ChunkTable, fallback: str = "") -> str:
    for row in reversed(chunk_table.rows):
        if row.kind == ChunkKind.USER:
            text = (row.payload.get("content") or "").strip()
            if text:
                return text[:40] + ("..." if len(text) > 40 else "")
    return fallback


def count_consecutive_low_mood(chunk_table: ChunkTable, max_scan: int = 6) -> int:
    """最近连续用户轮次是否偏负面"""
    streak = 0
    scanned = 0
    for row in reversed(chunk_table.rows):
        if row.kind != ChunkKind.USER:
            continue
        scanned += 1
        if scanned > max_scan:
            break
        text = row.payload.get("content", "")
        if any(w in text for w in _NEGATIVE):
            streak += 1
        else:
            break
    return streak
