from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class Plan(StrEnum):
    OBSERVER = "observer"
    OPERATOR = "operator"
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
