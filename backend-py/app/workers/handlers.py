"""Default task handlers kept independent from the FastAPI process."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.tasks.service import TaskHandler
from app.config import get_settings
from app.repositories.factory import get_repositories
from xiaoman.achievements import check_achievements
from xiaoman.llm_service import LLMClient
from xiaoman.memory import MemoryEngine
from xiaoman.reports import generate_monthly_report, generate_weekly_report
from xiaoman.world import WorldSystem


@lru_cache(maxsize=1)
def _memory_engine() -> MemoryEngine:
    settings = get_settings()
    repositories = get_repositories()
    engine = MemoryEngine(LLMClient(), memory_repository=repositories.memory if settings.uses_postgres else None)
    engine.set_world_getter(lambda user_id: WorldSystem(user_id))
    return engine


def _memory_extract(task: dict[str, Any]) -> dict[str, Any]:
    payload = dict(task.get("payload") or {})
    return _memory_engine().extractor.extract_now(
        user_id=str(task["user_id"]),
        session_id=str(payload["session_id"]),
        messages=list(payload.get("messages") or []),
    )


def _dreaming(task: dict[str, Any]) -> dict[str, Any]:
    user_id = str(task["user_id"])
    return _memory_engine().run_nightly_flow(user_id, world=WorldSystem(user_id))


def _weekly_report(task: dict[str, Any]) -> dict[str, Any]:
    return generate_weekly_report(str(task["user_id"]), force=True)


def _monthly_report(task: dict[str, Any]) -> dict[str, Any]:
    return generate_monthly_report(str(task["user_id"]), force=True)


def _achievement_check(task: dict[str, Any]) -> dict[str, Any]:
    return {"newly_unlocked": check_achievements(str(task["user_id"]))}


def default_handlers() -> dict[str, TaskHandler]:
    return {
        "memory_extract": _memory_extract,
        "dreaming": _dreaming,
        "weekly_report": _weekly_report,
        "monthly_report": _monthly_report,
        "achievement_check": _achievement_check,
    }
