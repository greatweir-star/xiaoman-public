"""Compatibility security boundary for the legacy Xiaoman API."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.auth.repository import AuthUser
from app.auth.service import AuthService, get_auth_service
from app.config import Settings, get_settings
from app.dependencies import RequestContext, _bearer_token, assert_owner_or_role

PUBLIC_API_PATHS = {"/api/health"}
PUBLIC_API_PREFIXES = ("/api/auth",)
OWNER_SCOPED_RESOURCES = {"world", "profile", "skill-tree", "memory"}


def legacy_requested_user_id(path: str) -> str | None:
    segments = [segment for segment in path.split("/") if segment]
    if len(segments) < 3 or segments[0] != "api":
        return None
    if segments[1] not in OWNER_SCOPED_RESOURCES:
        return None
    return segments[2]


def is_public_api_path(path: str) -> bool:
    return path in PUBLIC_API_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_API_PREFIXES)


def authorize_legacy_api_request(
    *,
    path: str,
    authorization: str | None,
    service: AuthService | None = None,
    settings: Settings | None = None,
) -> AuthUser | None:
    """Authorize an API request while local development is still file-backed."""

    runtime_settings = settings or get_settings()
    if not path.startswith("/api/") or is_public_api_path(path) or not runtime_settings.requires_auth:
        return None

    auth_service = service or get_auth_service()
    user = auth_service.get_user_from_access_token(_bearer_token(authorization))
    requested_user_id = legacy_requested_user_id(path)
    if requested_user_id:
        assert_owner_or_role(
            requested_user_id,
            RequestContext(tenant_id=user.tenant_id, user_id=user.id, roles=("user",)),
        )
    return user


def resolve_ws_auth_user_id(
    message: dict[str, Any],
    *,
    service: AuthService | None = None,
    settings: Settings | None = None,
) -> str:
    """Resolve the authenticated WebSocket user, with a local compatibility mode."""

    runtime_settings = settings or get_settings()
    requested_user_id = str(message.get("userId") or "")
    access_token = str(message.get("accessToken") or message.get("access_token") or "")

    if access_token:
        auth_service = service or get_auth_service()
        user = auth_service.get_user_from_access_token(access_token)
        if requested_user_id and requested_user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user.id

    if runtime_settings.requires_auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing websocket access token")
    if not requested_user_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="missing user id")
    return requested_user_id


class LegacyApiAuthMiddleware(BaseHTTPMiddleware):
    """Protect old REST routes until they move behind repository-backed routers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)
        try:
            user = authorize_legacy_api_request(
                path=request.url.path,
                authorization=request.headers.get("Authorization"),
            )
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        if user:
            request.state.auth_user = user
        return await call_next(request)
