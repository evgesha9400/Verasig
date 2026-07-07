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


def require_source_capacity(
    user: UserAccount, session: Session, channel_id: int | None = None
) -> None:
    limit = PLAN_LIMITS[user.plan].sources
    if limit is None:
        return
    # re-adding a feed the user already owns is not a new source; it must not be
    # blocked by the limit (nor double-counted against it).
    if channel_id is not None and (
        feed_repository.read_feed(session, user.id, channel_id) is not None
    ):
        return
    if feed_repository.count_feeds(session, user.id) >= limit:
        raise PlanSourceLimitExceeded
