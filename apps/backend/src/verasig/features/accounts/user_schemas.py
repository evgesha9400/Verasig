from datetime import datetime

from verasig.domain.account import UserAccount
from verasig.foundation.http.schemas import CamelModel


class UserOut(CamelModel):
    first_name: str
    last_name: str
    email: str
    plan: str
    pending_email: str | None
    cancel_at: datetime | None


def user_out(account: UserAccount) -> UserOut:
    return UserOut(
        first_name=account.first_name,
        last_name=account.last_name,
        email=account.email,
        plan=account.plan.value,
        pending_email=account.pending_email,
        cancel_at=account.cancel_at,
    )
