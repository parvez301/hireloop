import pytest

from hireloop.services.rate_limit import InMemoryRateLimiter, RateLimiter, RateLimitError


class FakeRedis:
    """Minimal fake: in-memory key/value + TTL."""

    def __init__(self):
        self.store: dict[str, str] = {}
        self.ttls: dict[str, float] = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = value
        if ex:
            self.ttls[key] = ex
        return True


@pytest.mark.asyncio
async def test_rate_limiter_allows_up_to_capacity():
    redis = FakeRedis()
    limiter = RateLimiter(redis, capacity=3, refill_per_second=0.05)
    for _ in range(3):
        await limiter.check("user-1")
    with pytest.raises(RateLimitError):
        await limiter.check("user-1")


@pytest.mark.asyncio
async def test_rate_limiter_isolates_users():
    redis = FakeRedis()
    limiter = RateLimiter(redis, capacity=1, refill_per_second=0.0)
    await limiter.check("user-a")
    await limiter.check("user-b")
    with pytest.raises(RateLimitError):
        await limiter.check("user-a")


@pytest.mark.asyncio
async def test_in_memory_rate_limiter_allows_up_to_capacity():
    limiter = InMemoryRateLimiter(capacity=3, refill_per_second=0.05)
    for _ in range(3):
        await limiter.check("user-1")
    with pytest.raises(RateLimitError):
        await limiter.check("user-1")
