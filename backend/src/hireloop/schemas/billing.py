from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CheckoutSessionOut(BaseModel):
    url: str


class PortalSessionOut(BaseModel):
    url: str


class SubscriptionOut(BaseModel):
    id: UUID
    user_id: UUID
    plan: str
    status: str
    trial_ends_at: datetime | None
    current_period_end: datetime | None
    past_due_since: datetime | None = None
    cancel_at_period_end: bool = False
    stripe_customer_id: str | None = None
    has_active_entitlement: bool
