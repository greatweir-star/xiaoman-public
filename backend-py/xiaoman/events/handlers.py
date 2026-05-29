"""EventBus 订阅 — PRD memory-02 事件驱动联动"""

from __future__ import annotations

import logging

from xiaoman.events.event_bus import EventBus, WorldEvent

logger = logging.getLogger(__name__)


def _on_user_input(event: WorldEvent) -> None:
    logger.debug("user_input user=%s session=%s", event.user_id, event.payload.get("session_id"))


def _on_linkage_triggered(event: WorldEvent) -> None:
    changes = event.payload.get("changes") or []
    if changes:
        names = [c.get("linkage", "?") for c in changes]
        logger.info("linkage_triggered user=%s linkages=%s", event.user_id, names)


def _on_emotion_detected(event: WorldEvent) -> None:
    logger.info(
        "emotion_detected user=%s emotion=%s source=%s",
        event.user_id,
        event.payload.get("emotion"),
        event.payload.get("source"),
    )


def register_memory_event_handlers(bus: EventBus) -> None:
    """注册记忆/联动相关事件订阅（启动时调用一次）"""
    bus.subscribe("user_input", _on_user_input)
    bus.subscribe("linkage_triggered", _on_linkage_triggered)
    bus.subscribe("emotion_detected", _on_emotion_detected)
