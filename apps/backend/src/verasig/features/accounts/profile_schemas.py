from verasig.domain.account import Plan
from verasig.foundation.http.schemas import CamelModel


class RenameUserIn(CamelModel):
    first_name: str | None = None
    last_name: str | None = None


class EmailChangeIn(CamelModel):
    email: str


class EmailConfirmIn(CamelModel):
    token: str


class SubscriptionChangeIn(CamelModel):
    plan: Plan
