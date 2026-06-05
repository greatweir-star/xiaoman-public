"""Authentication routes for the V0.03 SaaS app shell."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.auth.models import LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest, TokenPair
from app.auth.service import AuthService, get_auth_service
from app.config import Settings, get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/health")
async def auth_health(settings: Settings = Depends(get_settings)) -> dict[str, str | bool]:
    return {"status": "ok", "auth_required": settings.requires_auth}


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    return service.register(email=body.email, password=body.password)


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    return service.login(email=body.email, password=body.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    return service.refresh(body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> Response:
    service.logout(body.refresh_token)
    return response
