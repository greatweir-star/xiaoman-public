"""Authenticated WebSocket connection context."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectionContext:
    tenant_id: str
    user_id: str
    companion_id: str = "xiaoman"
    session_id: str = ""
