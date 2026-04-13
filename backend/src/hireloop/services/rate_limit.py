"""Redis token-bucket rate limiter.

Key format: rl:{bucket_name}:{subject}
Value: JSON `{tokens: float, updated_at: float_unix_seconds}`

On check(): compute refill since updated_at, subtract 1, persist.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from redis.asyncio import Redis


class RateLimitError(Exception):
    def __init__(self, retry_after_s: float):
        super().__init__(f"Rate limit exceeded; retry after {retry_after_s:.1f}s")
        self.retry_after_s = retry_after_s


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
