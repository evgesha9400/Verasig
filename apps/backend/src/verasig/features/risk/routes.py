from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request

from verasig.domain.feed import FeedStatus
from verasig.domain.risk_config import RiskConfig
from verasig.features.feeds import feed_repository
from verasig.features.risk.repository import read_risk_config, upsert_risk_config
from verasig.features.risk.schemas import RiskConfigBody, to_body, to_config
from verasig.features.simulation import repository as backtest_repository
from verasig.foundation.http.auth_dependencies import require_feed

router = APIRouter(prefix="/feeds/{external_id}")


@router.get("/risk")
def get_risk(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
) -> RiskConfigBody:
    with request.app.state.session_factory() as session:
        config = read_risk_config(
            session, subscription.user_id, subscription.external_id
        )
    return to_body(config or RiskConfig())


@router.put("/risk")
def put_risk(
    request: Request,
    external_id: str,
    payload: RiskConfigBody,
    subscription=Depends(require_feed),
) -> RiskConfigBody:
    user_id, channel_id = subscription.user_id, subscription.external_id
    with request.app.state.session_factory() as session:
        previous = read_risk_config(session, user_id, channel_id) or RiskConfig()
        config = upsert_risk_config(
            session, user_id, channel_id, to_config(payload), datetime.now(tz=UTC)
        )
        if config != previous:
            _invalidate_backtest(session, subscription)
        session.commit()
    return to_body(config)


def _invalidate_backtest(session, subscription) -> None:
    """A backtest priced under the previous risk model no longer applies."""
    user_id, channel_id = subscription.user_id, subscription.external_id
    backtest_repository.delete_results_for_channel(session, user_id, channel_id)
    if subscription.status == FeedStatus.ANALYZED:
        feed_repository.set_status(session, user_id, channel_id, FeedStatus.VERIFIED)
