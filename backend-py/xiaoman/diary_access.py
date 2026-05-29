"""日记访问控制 — PRD xiaoman-flows C4"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def annotate_diary_entries(
    entries: list[dict[str, Any]],
    *,
    relation_level: int,
    unlock_level: int = 3,
    lock_after_days: int = 2,
) -> list[dict[str, Any]]:
    """为日记条目标注锁定状态（关系等级不足时，较早日记不可读）"""
    today = date.today()
    result: list[dict[str, Any]] = []
    for entry in entries:
        item = dict(entry)
        entry_date = _parse_date(item.get("date", ""))
        days_old = (today - entry_date).days if entry_date else 0
        locked = relation_level < unlock_level and days_old > lock_after_days
        item["locked"] = locked
        if locked:
            item["unlock_hint"] = f"关系达到「树洞」（L{unlock_level}）后可查看更早日记"
        else:
            item.pop("unlock_hint", None)
        result.append(item)
    return result


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except (ValueError, TypeError):
        return None
