from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedORM(ORMModel):
    id: UUID
    created_at: datetime
    updated_at: datetime


class MetaModel(BaseModel):
    cached: bool | None = None
    tokens_used: int | None = None
    cost_cents: int | None = None


class Envelope[T](BaseModel):
    data: T
    meta: MetaModel | None = None
