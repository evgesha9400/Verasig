from dataclasses import dataclass

from sqlalchemy.orm import Session

from verasig.api.errors import ApiError
from verasig.domain.account import Plan, UserAccount
from verasig.storage.user_channel_repository import count_subscriptions


@dataclass(frozen=True)
class PlanLimits:
    sources: int | None
    signals_per_month: int | None
    exchanges: int | None


PLAN_LIMITS = {
    Plan.OBSERVER: PlanLimits(sources=1, signals_per_month=200, exchanges=0),
    Plan.OPERATOR: PlanLimits(sources=10, signals_per_month=None, exchanges=1),
    Plan.DESK: PlanLimits(sources=None, signals_per_month=None, exchanges=None),
}


def require_source_capacity(user: UserAccount, session: Session) -> None:
    limit = PLAN_LIMITS[user.plan].sources
    if limit is None:
        return
    if count_subscriptions(session, user.id) >= limit:
        raise ApiError(403, "PLAN_LIMIT_SOURCES", "Source limit reached")
