"""User-level fixed-window rate limiting with Redis and memory fallback."""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass
from typing import Protocol

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class RateLimitBackend(Protocol):
    def hit(self, key: str, *, limit: int, window_seconds: int, now: float | None = None) -> RateLimitDecision:
        ...


def _decision(count: int, *, limit: int, window_seconds: int, now: float) -> RateLimitDecision:
    remaining = max(limit - count, 0)
    retry_after = max(math.ceil(window_seconds - (now % window_seconds)), 1)
    return RateLimitDecision(
        allowed=count <= limit,
        limit=limit,
        remaining=remaining,
        retry_after_seconds=retry_after,
    )


class MemoryRateLimitBackend:
    def __init__(self) -> None:
        self._counts: dict[str, tuple[int, int]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, *, limit: int, window_seconds: int, now: float | None = None) -> RateLimitDecision:
        timestamp = time.time() if now is None else now
        window = int(timestamp // window_seconds)
        with self._lock:
            previous_window, previous_count = self._counts.get(key, (window, 0))
            count = previous_count + 1 if previous_window == window else 1
            self._counts[key] = (window, count)
        return _decision(count, limit=limit, window_seconds=window_seconds, now=timestamp)


class RedisRateLimitBackend:
    def __init__(self, redis_url: str) -> None:
        try:
            import redis
        except ImportError as exc:  # pragma: no cover - exercised only in incomplete deployments
            raise RuntimeError("redis package is required for Redis rate limiting") from exc
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)

    def hit(self, key: str, *, limit: int, window_seconds: int, now: float | None = None) -> RateLimitDecision:
        timestamp = time.time() if now is None else now
        window = int(timestamp // window_seconds)
        redis_key = f"rate:{key}:{window}"
        pipeline = self.client.pipeline()
        pipeline.incr(redis_key)
        pipeline.expire(redis_key, window_seconds * 2)
        count = int(pipeline.execute()[0])
        return _decision(count, limit=limit, window_seconds=window_seconds, now=timestamp)


class RateLimitService:
    def __init__(
        self,
        backend: RateLimitBackend,
        *,
        limit: int,
        window_seconds: int,
        fallback: RateLimitBackend | None = None,
    ) -> None:
        self.backend = backend
        self.fallback = fallback
        self.limit = max(limit, 0)
        self.window_seconds = max(window_seconds, 1)

    def check(self, *, tenant_id: str, user_id: str) -> RateLimitDecision:
        if self.limit == 0:
            return RateLimitDecision(allowed=True, limit=0, remaining=0, retry_after_seconds=0)
        key = f"{tenant_id}:{user_id}"
        try:
            return self.backend.hit(key, limit=self.limit, window_seconds=self.window_seconds)
        except Exception:
            if not self.fallback:
                raise
            logger.warning("Redis rate limiter unavailable; using in-memory fallback", exc_info=True)
            return self.fallback.hit(key, limit=self.limit, window_seconds=self.window_seconds)


def create_rate_limit_service(settings: Settings | None = None) -> RateLimitService:
    resolved = settings or get_settings()
    memory = MemoryRateLimitBackend()
    backend: RateLimitBackend = memory
    fallback: RateLimitBackend | None = None
    if resolved.redis_url:
        try:
            backend = RedisRateLimitBackend(resolved.redis_url)
            fallback = memory
        except RuntimeError:
            logger.warning("Redis rate limiter could not initialize; using in-memory backend", exc_info=True)
    return RateLimitService(
        backend,
        limit=resolved.rate_limit_messages,
        window_seconds=resolved.rate_limit_window_seconds,
        fallback=fallback,
    )
