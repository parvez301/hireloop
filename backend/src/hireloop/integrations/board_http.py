"""Shared httpx client for public job-board APIs.

Applies a per-platform token-bucket rate limit so we stay polite with the
public APIs. Configured via `SCAN_BOARD_RATE_LIMIT_REQS_PER_SEC`.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from hireloop.config import get_settings

_USER_AGENT = "HireLoop/1.0 (+https://careeragent.com/bot)"
_DEFAULT_TIMEOUT_S = 10.0

_platform_last_request: dict[str, float] = defaultdict(float)
_platform_lock: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


async def _rate_limit(platform: str) -> None:
    settings = get_settings()
    min_interval = 1.0 / max(0.1, settings.scan_board_rate_limit_reqs_per_sec)
    async with _platform_lock[platform]:
        now = time.monotonic()
        last = _platform_last_request[platform]
        elapsed = now - last
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        _platform_last_request[platform] = time.monotonic()


@asynccontextmanager
async def board_client() -> AsyncIterator[httpx.AsyncClient]:
    """Yield a configured async httpx client for one operation."""
    async with httpx.AsyncClient(
        timeout=_DEFAULT_TIMEOUT_S,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
    ) as client:
        yield client


async def get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    platform: str,
    max_attempts: int = 3,
) -> httpx.Response:
    """GET with exponential-backoff retry and platform rate limiting."""
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            await _rate_limit(platform)
            response = await client.get(url)
            if response.status_code >= 500:
                last_exc = httpx.HTTPStatusError(
                    f"{url} returned {response.status_code}",
                    request=response.request,
                    response=response,
                )
                await asyncio.sleep(min(4.0, 0.5 * (2**attempt)))
                continue
            return response
        except httpx.HTTPError as e:
            last_exc = e
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(min(4.0, 0.5 * (2**attempt)))
    if last_exc:
        raise last_exc
    raise RuntimeError("unreachable")
