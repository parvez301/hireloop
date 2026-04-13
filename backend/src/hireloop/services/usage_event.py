"""Write-path for usage_events — all LLM calls funnel through here."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.models.usage_event import UsageEvent


class UsageEventService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        *,
        user_id: UUID,
        event_type: str,
        module: str | None,
        model: str | None,
        tokens_used: int | None,
        cost_cents: int | None,
    ) -> UsageEvent:
        row = UsageEvent(
            user_id=user_id,
            event_type=event_type,
            module=module,
            model=model,
            tokens_used=tokens_used,
            cost_cents=cost_cents,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def record_many(self, events: Iterable[dict[str, Any]]) -> None:
        rows = [UsageEvent(**e) for e in events]
        self.session.add_all(rows)
        await self.session.flush()
