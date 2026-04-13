from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OfferDetails(BaseModel):
    base: int = Field(..., ge=0, description="Base salary in USD")
    equity: str | None = None
    signing_bonus: int | None = None
    total_comp: int | None = None
    location: str | None = None
    start_date: str | None = None


class NegotiationCreate(BaseModel):
    job_id: UUID
    offer_details: OfferDetails


class NegotiationRegenerate(BaseModel):
    feedback: str | None = None


class NegotiationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    job_id: UUID
    offer_details: dict[str, Any]
    market_research: dict[str, Any]
    counter_offer: dict[str, Any]
    scripts: dict[str, Any]
    model_used: str
    tokens_used: int | None
    created_at: datetime
