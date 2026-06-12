from verasig.api.schemas.common import CamelModel
from verasig.domain.account import Plan


class RenameUserIn(CamelModel):
    first_name: str | None = None
    last_name: str | None = None


class EmailChangeIn(CamelModel):
    email: str


class EmailConfirmIn(CamelModel):
    token: str


class SubscriptionChangeIn(CamelModel):
    plan: Plan
