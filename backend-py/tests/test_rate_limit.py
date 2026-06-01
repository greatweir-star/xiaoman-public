from app.services.rate_limit import MemoryRateLimitBackend, RateLimitService


class FailingBackend:
    def hit(self, key, *, limit, window_seconds, now=None):
        raise ConnectionError("redis unavailable")


def test_memory_rate_limit_resets_at_next_window():
    backend = MemoryRateLimitBackend()

    assert backend.hit("tenant:user", limit=2, window_seconds=60, now=1).allowed
    assert backend.hit("tenant:user", limit=2, window_seconds=60, now=2).allowed
    denied = backend.hit("tenant:user", limit=2, window_seconds=60, now=3)
    assert not denied.allowed
    assert denied.remaining == 0
    assert backend.hit("tenant:user", limit=2, window_seconds=60, now=61).allowed


def test_rate_limit_service_uses_memory_fallback():
    service = RateLimitService(
        FailingBackend(),
        limit=1,
        window_seconds=60,
        fallback=MemoryRateLimitBackend(),
    )

    assert service.check(tenant_id="tenant-1", user_id="user-1").allowed
    assert not service.check(tenant_id="tenant-1", user_id="user-1").allowed


def test_zero_limit_disables_rate_limiting():
    service = RateLimitService(MemoryRateLimitBackend(), limit=0, window_seconds=60)

    assert service.check(tenant_id="tenant-1", user_id="user-1").allowed
