"""Inngest client singleton.

Uses dev mode (no signing key required) when INNGEST_DEV=true. In production,
both INNGEST_EVENT_KEY and INNGEST_SIGNING_KEY must be populated.
"""

from __future__ import annotations

from functools import lru_cache

import inngest

from hireloop.config import get_settings


@lru_cache(maxsize=1)
def get_inngest_client() -> inngest.Inngest:
    settings = get_settings()
    return inngest.Inngest(
        app_id="hireloop",
        event_key=settings.inngest_event_key or None,
        signing_key=settings.inngest_signing_key or None,
        is_production=not settings.inngest_dev,
    )
