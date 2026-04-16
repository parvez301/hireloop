"""Redis token-bucket rate limiter + in-process fallback when REDIS_URL is empty (Lambda).

Key format: rl:{bucket_name}:{subject}
Value: JSON `{tokens: float, updated_at: float_unix_seconds}`

On check(): compute refill since updated_at, subtract 1, persist.

In-memory fallback: per-process (Lambda warm container); not shared across invocations.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Protocol

from redis.asyncio import Redis


class RateLimitError(Exception):
    def __init__(self, retry_after_s: float):
        super().__init__(f"Rate limit exceeded; retry after {retry_after_s:.1f}s")
        self.retry_after_s = retry_after_s


class SupportsRateCheck(Protocol):
    async def check(self, subject: str) -> None: ...


@dataclass
class RateLimiter:
    redis: Redis
    capacity: int
    refill_per_second: float
    bucket_name: str = "msg"
    ttl_s: int = 120

    async def check(self, subject: str) -> None:
        key = f"rl:{self.bucket_name}:{subject}"
        now = time.time()

        raw = await self.redis.get(key)
        if raw is None:
            state = {"tokens": float(self.capacity), "updated_at": now}
        else:
            state = json.loads(raw if isinstance(raw, str) else raw.decode())

        elapsed = max(0.0, now - float(state["updated_at"]))
        refilled = min(
            float(self.capacity),
            float(state["tokens"]) + elapsed * self.refill_per_second,
        )

        if refilled < 1.0:
            needed = 1.0 - refilled
            retry_after = needed / self.refill_per_second if self.refill_per_second > 0 else 60.0
            raise RateLimitError(retry_after_s=retry_after)

        refilled -= 1.0
        new_state = {"tokens": refilled, "updated_at": now}
        await self.redis.set(key, json.dumps(new_state), ex=self.ttl_s)


@dataclass
class InMemoryRateLimiter:
    """Token-bucket limiter in asyncio memory (Lambda without Redis)."""

    capacity: int
    refill_per_second: float
    bucket_name: str = "msg"
    ttl_s: int = 120
    _lock: asyncio.Lock = field(init=False, repr=False)
    _state: dict[str, dict[str, float]] = field(init=False, repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._lock = asyncio.Lock()

    async def check(self, subject: str) -> None:
        key = f"rl:{self.bucket_name}:{subject}"
        now = time.time()
        async with self._lock:
            raw = self._state.get(key)
            if raw is None:
                state = {"tokens": float(self.capacity), "updated_at": now}
            else:
                state = dict(raw)

            elapsed = max(0.0, now - float(state["updated_at"]))
            refilled = min(
                float(self.capacity),
                float(state["tokens"]) + elapsed * self.refill_per_second,
            )

            if refilled < 1.0:
                needed = 1.0 - refilled
                rps = self.refill_per_second
                retry_after = needed / rps if rps > 0 else 60.0
                raise RateLimitError(retry_after_s=retry_after)

            refilled -= 1.0
            self._state[key] = {"tokens": refilled, "updated_at": now}
