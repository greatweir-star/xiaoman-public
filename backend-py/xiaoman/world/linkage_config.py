"""YAML 配置化联动链路 — 参考 memory-02-flows §5 + linkage-extension-design"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config", "linkages")


@dataclass
class LinkageDefinition:
    name: str
    priority: int = 50
    mutex_group: str = ""
    enabled: bool = True
    min_relation_xp: int = 0
    triggers: list[dict[str, Any]] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)


def load_linkage_definitions(config_dir: str | None = None) -> list[LinkageDefinition]:
    directory = Path(config_dir or CONFIG_DIR)
    if not directory.exists():
        logger.warning("Linkage config dir not found: %s", directory)
        return []

    definitions: list[LinkageDefinition] = []
    for file in sorted(directory.glob("*.yaml")):
        try:
            raw = yaml.safe_load(file.read_text(encoding="utf-8"))
            if not raw or not raw.get("enabled", True):
                continue
            definitions.append(
                LinkageDefinition(
                    name=raw.get("name", file.stem),
                    priority=int(raw.get("priority", 50)),
                    mutex_group=raw.get("mutex_group", ""),
                    enabled=bool(raw.get("enabled", True)),
                    min_relation_xp=int(raw.get("min_relation_xp", 0)),
                    triggers=raw.get("triggers") or [],
                    actions=raw.get("actions") or [],
                )
            )
        except Exception:
            logger.exception("Failed to load linkage %s", file)
    return sorted(definitions, key=lambda d: d.priority, reverse=True)


def evaluate_triggers(defn: LinkageDefinition, user_text: str, changes: list[dict[str, Any]], context: dict[str, Any]) -> bool:
    if not defn.triggers:
        return False

    for trigger in defn.triggers:
        if _match_trigger(trigger, user_text, changes, context):
            return True
    return False


def _match_trigger(
    trigger: dict[str, Any],
    user_text: str,
    changes: list[dict[str, Any]],
    context: dict[str, Any],
) -> bool:
    ttype = trigger.get("type")

    if ttype == "keyword":
        keywords = trigger.get("keywords") or []
        return any(kw in user_text for kw in keywords)

    if ttype == "change":
        layer = trigger.get("layer")
        change = trigger.get("change")
        for c in changes:
            if c.get("layer") == layer and (not change or c.get("change") == change):
                return True
        return False

    if ttype == "emotion":
        emotion = context.get("user_emotion", "")
        return emotion in (trigger.get("values") or [])

    if ttype == "time":
        hour = context.get("hour", 12)
        start, end = trigger.get("range", [0, 24])
        if start <= end:
            return start <= hour < end
        return hour >= start or hour < end

    if ttype == "composite":
        op = trigger.get("operator", "OR").upper()
        conditions = trigger.get("conditions") or []
        results = [_match_trigger(c, user_text, changes, context) for c in conditions]
        return all(results) if op == "AND" else any(results)

    if ttype == "semantic":
        intents = trigger.get("intents") or {}
        for intent, keywords in intents.items():
            if any(kw in user_text for kw in keywords):
                context["detected_intent"] = intent
                return True
        return False

    if ttype == "state_check":
        field = trigger.get("field", "relation_xp")
        op = trigger.get("operator", "gte")
        threshold = int(trigger.get("threshold", 0))
        value = int(context.get(field, 0))
        if op == "gte":
            return value >= threshold
        if op == "lte":
            return value <= threshold
        if op == "gt":
            return value > threshold
        if op == "lt":
            return value < threshold
        return value == threshold

    if ttype == "birthday":
        days_before = int(trigger.get("days_before", 3))
        days_until = context.get("birthday_days_until")
        if days_until is None:
            return False
        return 0 <= int(days_until) <= days_before

    return False


def resolve_conflicts(triggered: list[tuple[LinkageDefinition, list[dict[str, Any]]]]) -> list[tuple[LinkageDefinition, list[dict[str, Any]]]]:
    """互斥组内只保留优先级最高的一条"""
    seen_groups: set[str] = set()
    result: list[tuple[LinkageDefinition, list[dict[str, Any]]]] = []
    for defn, effects in triggered:
        group = defn.mutex_group
        if group and group in seen_groups:
            continue
        if group:
            seen_groups.add(group)
        result.append((defn, effects))
    return result
