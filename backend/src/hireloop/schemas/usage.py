from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UsageEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    event_type: str
    module: str | None
    model: str | None
    tokens_used: int | None
    cost_cents: int | None
    created_at: datetime
