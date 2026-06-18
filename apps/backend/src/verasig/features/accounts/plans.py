from dataclasses import dataclass

from sqlalchemy.orm import Session

from verasig.domain.account import Plan, UserAccount
from verasig.features.feeds import feed_repository


class PlanSourceLimitExceeded(Exception):
    """Raised when a user has reached their source subscription limit."""


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
    if feed_repository.count_feeds(session, user.id) >= limit:
        raise PlanSourceLimitExceeded
