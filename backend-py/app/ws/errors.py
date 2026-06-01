"""Stable WebSocket error codes shared with frontend clients."""

from __future__ import annotations

from typing import Any

AUTH_FAILED = "auth_failed"
INVALID_MESSAGE = "invalid_message"
MODEL_ERROR = "model_error"
RATE_LIMITED = "rate_limited"


def ws_error_payload(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}
