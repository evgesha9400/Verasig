from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class Plan(StrEnum):
    FREE = "free"
    TRADER = "trader"
    DESK = "desk"


@dataclass(frozen=True)
class UserAccount:
    id: UUID
    email: str
    password_hash: str
    first_name: str
    last_name: str
    plan: Plan
    pending_email: str | None
    cancel_at: datetime | None
    created_at: datetime
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    subscription_status: str | None = None
    stripe_checkout_session_id: str | None = None
    stripe_event_at: datetime | None = None
