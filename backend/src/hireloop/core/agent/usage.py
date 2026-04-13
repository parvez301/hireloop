"""Helper: write the turn's accumulated model_calls into usage_events."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.services.usage_event import UsageEventService


async def record_turn_usage(
    session: AsyncSession,
    user_id: UUID,
    model_calls: list[dict[str, Any]],
) -> None:
    if not model_calls:
        return
    service = UsageEventService(session)
    for call in model_calls:
        await service.record(
            user_id=user_id,
            event_type=call.get("event_type", "respond"),
            module=call.get("module", "agent"),
            model=call.get("model"),
            tokens_used=call.get("tokens_used"),
            cost_cents=call.get("cost_cents"),
        )
