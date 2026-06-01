"""Authenticated usage query routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth.repository import AuthUser
from app.dependencies import get_current_user
from app.services.usage import UsageService

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/me")
async def my_usage(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: AuthUser = Depends(get_current_user),
) -> dict:
    return UsageService().summarize_user(current_user.tenant_id, current_user.id, limit)
