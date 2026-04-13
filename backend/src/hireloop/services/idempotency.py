"""Redis-backed Idempotency-Key support for POST endpoints."""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

_TTL_S = 60 * 60 * 24


class IdempotencyStore:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, user_id: str, key: str) -> dict[str, Any] | None:
        raw = await self.redis.get(self._key(user_id, key))
        if raw is None:
            return None
        decoded = raw if isinstance(raw, str) else raw.decode()
        parsed: dict[str, Any] = json.loads(decoded)
        return parsed

    async def set(self, user_id: str, key: str, response_body: dict[str, Any]) -> None:
        await self.redis.set(self._key(user_id, key), json.dumps(response_body), ex=_TTL_S)

    @staticmethod
    def _key(user_id: str, key: str) -> str:
        return f"idem:{user_id}:{key}"
