"""Per-call LLM usage accounting."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import Settings, get_settings
from app.repositories import UsageRepository
from app.repositories.factory import get_repositories


def _tokens(usage: dict[str, Any], key: str) -> int:
    return max(int(usage.get(key) or 0), 0)


class UsageService:
    def __init__(self, repository: UsageRepository | None = None, settings: Settings | None = None) -> None:
        self.repository = repository or get_repositories().usage
        self.settings = settings or get_settings()

    def record_llm_call(
        self,
        *,
        tenant_id: str,
        user_id: str,
        session_id: str | None,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        usage = dict(event.get("usage") or {})
        prompt_tokens = _tokens(usage, "prompt_tokens")
        completion_tokens = _tokens(usage, "completion_tokens")
        cost_estimate = (
            prompt_tokens * self.settings.llm_prompt_cost_per_1m
            + completion_tokens * self.settings.llm_completion_cost_per_1m
        ) / 1_000_000
        record = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "session_id": session_id or None,
            "provider": str(event.get("provider") or "openai-compatible"),
            "model": str(event.get("model") or "unknown"),
            "request_type": str(event.get("request_type") or "chat"),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "embedding_tokens": _tokens(usage, "embedding_tokens"),
            "image_count": max(int(event.get("image_count") or 0), 0),
            "cost_estimate": round(cost_estimate, 8),
            "latency_ms": max(int(event.get("latency_ms") or 0), 0),
            "status": str(event.get("status") or "success"),
            "metadata": dict(event.get("metadata") or {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.repository.record(record)
        return record

    def summarize_user(self, tenant_id: str, user_id: str, limit: int = 100) -> dict[str, Any]:
        records = self.repository.list_for_user(tenant_id, user_id, limit=min(max(limit, 1), 500))
        return {
            "records": records,
            "total_prompt_tokens": sum(int(row.get("prompt_tokens") or 0) for row in records),
            "total_completion_tokens": sum(int(row.get("completion_tokens") or 0) for row in records),
            "total_cost_estimate": round(sum(float(row.get("cost_estimate") or 0) for row in records), 8),
        }
