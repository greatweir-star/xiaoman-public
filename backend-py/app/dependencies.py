"""FastAPI dependencies for the SaaS migration."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from app.auth.repository import AuthUser
from app.auth.service import AuthService, get_auth_service


@dataclass(frozen=True)
class RequestContext:
    tenant_id: str
    user_id: str
    roles: tuple[str, ...] = ()


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid authorization header")
    return token


async def get_current_user(
    authorization: str | None = Header(default=None),
    service: AuthService = Depends(get_auth_service),
) -> AuthUser:
    token = _bearer_token(authorization)
    return service.get_user_from_access_token(token)


async def get_request_context(
    current_user: AuthUser = Depends(get_current_user),
) -> RequestContext:
    """Return the authenticated request context.

    Legacy routes can compare their path-level user id with this context until
    the public API fully moves to `/api/me/...`.
    """

    return RequestContext(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        roles=("user",),
    )


def assert_owner_or_role(
    requested_user_id: str,
    context: RequestContext,
    *,
    allowed_roles: tuple[str, ...] = ("admin", "parent"),
) -> None:
    if requested_user_id == context.user_id:
        return
    if any(role in context.roles for role in allowed_roles):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
