"""用户真实姓名解析 — 从 L1 / 记忆事实中抽取，避免 LLM 编造示例名"""

from __future__ import annotations

import re
from typing import Any

_NAME_QUERY_RE = re.compile(
    r"(叫什么|名字是|名字叫|还记得我|我的名|称呼我|怎么称呼)",
)
_SELF_NAME_PATTERNS = (
    re.compile(r"我(?:的名字)?叫([\u4e00-\u9fa5a-zA-Z·]{1,12})"),
    re.compile(r"用户叫([\u4e00-\u9fa5a-zA-Z·]{1,12})"),
    re.compile(r"(?:名字|称呼)(?:是|叫)([\u4e00-\u9fa5a-zA-Z·]{1,12})"),
)
_COMPANION_NAME_HINTS = frozenset(
    {"小满", "小言", "桃桃", "鹿鸣", "阿梨", "同桌", "闺蜜", "朋友"},
)


def is_name_recall_query(text: str) -> bool:
    return bool(_NAME_QUERY_RE.search(text or ""))


def extract_name_from_text(text: str) -> str | None:
    """从单条事实/对话中解析用户自称的名字。"""
    raw = (text or "").strip()
    if not raw:
        return None
    for pattern in _SELF_NAME_PATTERNS:
        match = pattern.search(raw)
        if match:
            name = match.group(1).strip()
            if name and name not in _COMPANION_NAME_HINTS:
                return name
    return None


def _iter_memory_texts(memories: list[dict[str, Any]]) -> list[str]:
    texts: list[str] = []
    for mem in memories:
        text = (mem.get("fact") or mem.get("content") or mem.get("text") or "").strip()
        if text:
            texts.append(text)
    return texts


def resolve_user_name_from_memories(
    facts: list[dict[str, Any]],
    organized: list[dict[str, Any]] | None = None,
    long_term: list[dict[str, Any]] | None = None,
) -> str:
    """从结构化记忆中解析用户名字（后者优先）。"""
    candidates: list[str] = []
    for text in _iter_memory_texts(facts):
        if name := extract_name_from_text(text):
            candidates.append(name)
    for source in (organized or [], long_term or []):
        for text in _iter_memory_texts(source):
            if name := extract_name_from_text(text):
                candidates.append(name)
    return candidates[-1] if candidates else ""


def resolve_user_display_name(
    *,
    identity_name: str = "",
    understanding_name: str = "",
    facts: list[dict[str, Any]] | None = None,
    organized: list[dict[str, Any]] | None = None,
    long_term: list[dict[str, Any]] | None = None,
) -> str:
    """合并多来源：L1 身份 > 记忆事实 > L7 理解。"""
    memory_name = resolve_user_name_from_memories(
        facts or [],
        organized=organized,
        long_term=long_term,
    )
    for candidate in (identity_name, memory_name, understanding_name):
        name = (candidate or "").strip()
        if name and name not in _COMPANION_NAME_HINTS:
            return name
    return ""


def collect_name_memory_snippets(
    facts: list[dict[str, Any]],
    organized: list[dict[str, Any]] | None = None,
    long_term: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """返回与名字相关、用于注入 prompt 的记忆条目。"""
    seen: set[str] = set()
    hits: list[dict[str, Any]] = []
    for mem in list(facts) + list(organized or []) + list(long_term or []):
        text = (mem.get("fact") or mem.get("content") or mem.get("text") or "").strip()
        if not text or text in seen:
            continue
        if extract_name_from_text(text) or any(k in text for k in ("叫", "名字", "称呼")):
            seen.add(text)
            hits.append(mem if isinstance(mem, dict) else {"fact": text})
    return hits


def build_user_name_prompt_block(display_name: str, *, is_name_query: bool = False) -> str:
    if display_name:
        block = f"【用户自称】{display_name}\n回答涉及用户名字时以此为准，不要编造其他名字。"
        return block + "\n\n"
    if is_name_query:
        return (
            "【名字回忆】用户正在问自己的名字。若没有明确记录，诚实说还不确定或请 TA 再告诉一次，"
            "不要编造「阿梨」等示例名字。\n\n"
        )
    return ""
