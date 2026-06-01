"""Authenticated background task status routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth.repository import AuthUser
from app.dependencies import get_current_user
from app.tasks.service import TaskService, get_task_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/me")
async def my_tasks(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: AuthUser = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> dict:
    return {"tasks": service.list_for_user(current_user.tenant_id, current_user.id, limit)}
