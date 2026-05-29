"""事件总线 — 借鉴 linkage-extension-design Event Bus"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

logger = logging.getLogger(__name__)

EventHandler = Callable[["WorldEvent"], None]


@dataclass
class WorldEvent:
    type: str
    user_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: WorldEvent) -> None:
        for handler in self._handlers.get(event.type, []):
            try:
                handler(event)
            except Exception:
                logger.exception("Event handler failed for %s", event.type)
        for handler in self._handlers.get("*", []):
            try:
                handler(event)
            except Exception:
                logger.exception("Wildcard event handler failed")


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
