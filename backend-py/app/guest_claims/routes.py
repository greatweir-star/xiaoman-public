"""Guest data claim API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.repository import AuthUser
from app.dependencies import get_current_user
from app.guest_claims.models import (
    ClaimGuestRequest,
    ClaimGuestResponse,
    GuestClaimTokenRequest,
    GuestClaimTokenResponse,
)
from app.guest_claims.service import GuestClaimService, get_guest_claim_service

router = APIRouter(prefix="/api/auth", tags=["guest-claim"])


@router.post("/guest-claim-token", response_model=GuestClaimTokenResponse)
async def guest_claim_token(
    body: GuestClaimTokenRequest,
    service: GuestClaimService = Depends(get_guest_claim_service),
) -> GuestClaimTokenResponse:
    return GuestClaimTokenResponse(**service.issue_token(body.guest_id))


@router.post("/claim-guest", response_model=ClaimGuestResponse)
async def claim_guest(
    body: ClaimGuestRequest,
    current_user: AuthUser = Depends(get_current_user),
    service: GuestClaimService = Depends(get_guest_claim_service),
) -> ClaimGuestResponse:
    return ClaimGuestResponse(**service.claim(guest_id=body.guest_id, claim_token=body.claim_token, user=current_user))
