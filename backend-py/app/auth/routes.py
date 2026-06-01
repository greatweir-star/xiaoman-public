"""Authentication routes for the V0.03 SaaS app shell."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.auth.models import LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest, TokenPair
from app.auth.service import AuthService, get_auth_service
from app.operations.service import AuditService, get_audit_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/health")
async def auth_health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
    audit: AuditService = Depends(get_audit_service),
) -> TokenPair:
    pair = service.register(email=body.email, password=body.password)
    audit.record(tenant_id=pair.user.tenant_id, user_id=pair.user.id, action="auth.register", resource="user")
    return pair


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
    audit: AuditService = Depends(get_audit_service),
) -> TokenPair:
    pair = service.login(email=body.email, password=body.password)
    audit.record(tenant_id=pair.user.tenant_id, user_id=pair.user.id, action="auth.login", resource="session")
    return pair


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
    audit: AuditService = Depends(get_audit_service),
) -> TokenPair:
    pair = service.refresh(body.refresh_token)
    audit.record(tenant_id=pair.user.tenant_id, user_id=pair.user.id, action="auth.refresh", resource="session")
    return pair


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    service: AuthService = Depends(get_auth_service),
    audit: AuditService = Depends(get_audit_service),
) -> Response:
    user = service.logout(body.refresh_token)
    if user:
        audit.record(tenant_id=user.tenant_id, user_id=user.id, action="auth.logout", resource="session")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
