"""回访开场 — PRD TC8 重开提及上次话题"""

from __future__ import annotations

from typing import Any


def build_returning_recall_line(
    *,
    last_topic: str = "",
    session_summary: str = "",
    memories: list[dict[str, Any]] | None = None,
    user_name: str = "",
) -> str:
    """生成回访一句钩子，空串表示无可用记忆。"""
    if last_topic:
        short = last_topic if len(last_topic) <= 24 else last_topic[:24] + "…"
        return f"对了，上次聊到「{short}」，后来怎么样了？"

    if memories:
        fact = (memories[0].get("fact") or memories[0].get("text") or "").strip()
        if fact:
            snippet = fact if len(fact) <= 28 else fact[:28] + "…"
            return f"我还记得你说过{snippet}，最近还好吗？"

    if session_summary:
        snippet = session_summary if len(session_summary) <= 30 else session_summary[:30] + "…"
        return f"我们之前聊过{snippet}，今天想继续吗？"

    name = (user_name or "").strip()
    if name:
        return f"嗨{name}，又见面啦～今天想聊点什么？"

    return ""
