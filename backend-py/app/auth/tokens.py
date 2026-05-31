"""Small HS256 token helpers for the SaaS auth foundation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any


class TokenError(ValueError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _json_b64(obj: dict[str, Any]) -> str:
    return _b64(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _sign(message: str, secret: str) -> str:
    return _b64(hmac.new(secret.encode("utf-8"), message.encode("ascii"), hashlib.sha256).digest())


def create_token(
    *,
    secret: str,
    subject: str,
    tenant_id: str,
    token_type: str,
    expires_in: int,
    roles: tuple[str, ...] = (),
    extra: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "type": token_type,
        "roles": list(roles),
        "iat": now,
        "exp": now + expires_in,
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    signing_input = f"{_json_b64(header)}.{_json_b64(payload)}"
    return f"{signing_input}.{_sign(signing_input, secret)}"


def decode_token(token: str, *, secret: str, expected_type: str | None = None) -> dict[str, Any]:
    try:
        header_raw, payload_raw, signature = token.split(".", 2)
    except ValueError as exc:
        raise TokenError("Malformed token") from exc

    signing_input = f"{header_raw}.{payload_raw}"
    expected_signature = _sign(signing_input, secret)
    if not hmac.compare_digest(signature, expected_signature):
        raise TokenError("Invalid token signature")

    try:
        header = json.loads(_b64decode(header_raw))
        payload = json.loads(_b64decode(payload_raw))
    except (json.JSONDecodeError, ValueError) as exc:
        raise TokenError("Invalid token payload") from exc

    if header.get("alg") != "HS256":
        raise TokenError("Unsupported token algorithm")

    if expected_type and payload.get("type") != expected_type:
        raise TokenError("Unexpected token type")

    if int(payload.get("exp", 0)) < int(time.time()):
        raise TokenError("Token expired")

    return payload


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

