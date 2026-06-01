"""Guest data claim orchestration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.auth.repository import DEFAULT_TENANT_ID, AuthUser
from app.auth.service import _token_secret
from app.auth.tokens import TokenError, create_token, decode_token, hash_token
from app.config import Settings, get_settings
from app.guest_claims.migration import FileGuestMigrator, validate_uuid
from app.guest_claims.repository import GuestClaimRepository, create_guest_claim_repository

CLAIM_TTL_SECONDS = 60 * 10


class GuestClaimService:
    def __init__(
        self,
        repository: GuestClaimRepository,
        migrator: FileGuestMigrator,
        settings: Settings | None = None,
    ) -> None:
        self.repository = repository
        self.migrator = migrator
        self.settings = settings or get_settings()

    def issue_token(self, guest_id: str) -> dict[str, object]:
        try:
            guest_id = validate_uuid(guest_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        if not self.migrator.has_guest_data(guest_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guest data not found")
        token = create_token(
            secret=_token_secret(self.settings),
            subject=guest_id,
            tenant_id=DEFAULT_TENANT_ID,
            token_type="guest_claim",
            expires_in=CLAIM_TTL_SECONDS,
        )
        self.repository.save_token(
            tenant_id=DEFAULT_TENANT_ID,
            guest_id=guest_id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=CLAIM_TTL_SECONDS),
        )
        return {"claim_token": token, "expires_in": CLAIM_TTL_SECONDS}

    def claim(self, *, guest_id: str, claim_token: str, user: AuthUser) -> dict[str, str]:
        try:
            guest_id = validate_uuid(guest_id)
            payload = decode_token(claim_token, secret=_token_secret(self.settings), expected_type="guest_claim")
        except (ValueError, TokenError) as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        if payload.get("sub") != guest_id or payload.get("tenant_id") != user.tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="claim token does not match guest")

        existing = self.repository.get_claim(tenant_id=user.tenant_id, guest_id=guest_id)
        if existing:
            if existing["user_id"] != user.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="guest data already claimed")
            if existing["status"] == "completed":
                return self._response(existing)

        token_hash = hash_token(claim_token)
        try:
            self.repository.reserve_token(tenant_id=user.tenant_id, guest_id=guest_id, token_hash=token_hash)
            self.repository.begin_claim(
                tenant_id=user.tenant_id,
                guest_id=guest_id,
                user_id=user.id,
                token_hash=token_hash,
            )
            result = self.migrator.migrate(guest_id=guest_id, user_id=user.id)
            claim = self.repository.complete_claim(
                tenant_id=user.tenant_id,
                guest_id=guest_id,
                archive_path=str(result["archive_path"]),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except Exception as exc:
            self.repository.fail_claim(tenant_id=user.tenant_id, guest_id=guest_id, error_message=str(exc))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="guest claim failed") from exc
        return self._response(claim)

    @staticmethod
    def _response(claim: dict[str, str]) -> dict[str, str]:
        return {
            "status": claim["status"],
            "guest_id": claim["guest_id"],
            "user_id": claim["user_id"],
            "archive_path": claim.get("archive_path") or "",
        }


_service = GuestClaimService(create_guest_claim_repository(), FileGuestMigrator())


def get_guest_claim_service() -> GuestClaimService:
    return _service
