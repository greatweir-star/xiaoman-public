"""Operational audit and safety event services."""

from __future__ import annotations

import uuid
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.operations.repository import (
    FileOperationalEventRepository,
    OperationalEventRepository,
    PostgresOperationalEventRepository,
)
from xiaoman.paths import DATA_DIR

logger = logging.getLogger(__name__)


def _base_record(*, tenant_id: str, user_id: str | None, metadata: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "user_id": user_id,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


class AuditService:
    def __init__(self, repository: OperationalEventRepository) -> None:
        self.repository = repository

    def record(
        self,
        *,
        tenant_id: str,
        user_id: str | None,
        action: str,
        resource: str = "",
        status: str = "success",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            self.repository.append(
                {
                    **_base_record(tenant_id=tenant_id, user_id=user_id, metadata=metadata),
                    "action": action,
                    "resource": resource,
                    "status": status,
                }
            )
        except Exception:
            logger.exception("Audit event persistence failed: action=%s", action)


class SafetyEventService:
    def __init__(self, repository: OperationalEventRepository) -> None:
        self.repository = repository

    def record(
        self,
        *,
        tenant_id: str,
        user_id: str | None,
        category: str,
        severity: str = "high",
        source: str = "chat",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            self.repository.append(
                {
                    **_base_record(tenant_id=tenant_id, user_id=user_id, metadata=metadata),
                    "category": category,
                    "severity": severity,
                    "source": source,
                    "status": "open",
                }
            )
        except Exception:
            logger.exception("Safety event persistence failed: category=%s", category)


@dataclass(frozen=True)
class OperationalServices:
    audit: AuditService
    safety: SafetyEventService


def create_operational_services(settings: Settings | None = None, *, data_dir: str = DATA_DIR) -> OperationalServices:
    resolved = settings or get_settings()
    if resolved.uses_postgres:
        if not resolved.database_url:
            raise RuntimeError("DATABASE_URL is required for PostgreSQL operational events")
        audit_repository = PostgresOperationalEventRepository(resolved.database_url, "audit_logs")
        safety_repository = PostgresOperationalEventRepository(resolved.database_url, "safety_events")
    else:
        root = Path(data_dir)
        audit_repository = FileOperationalEventRepository(root / "audit_logs.jsonl")
        safety_repository = FileOperationalEventRepository(root / "safety_events.jsonl")
    return OperationalServices(audit=AuditService(audit_repository), safety=SafetyEventService(safety_repository))


@lru_cache(maxsize=1)
def get_operational_services() -> OperationalServices:
    return create_operational_services()


def get_audit_service() -> AuditService:
    return get_operational_services().audit
