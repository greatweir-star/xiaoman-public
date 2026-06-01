"""Request and response models for guest data claims."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GuestClaimTokenRequest(BaseModel):
    guest_id: str = Field(min_length=36, max_length=36)


class GuestClaimTokenResponse(BaseModel):
    claim_token: str
    expires_in: int


class ClaimGuestRequest(BaseModel):
    guest_id: str = Field(min_length=36, max_length=36)
    claim_token: str = Field(min_length=16)


class ClaimGuestResponse(BaseModel):
    status: str
    guest_id: str
    user_id: str
    archive_path: str = ""
