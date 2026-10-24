import asyncio
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from verasig.domain.feed import REVIEWED_STATUSES
from verasig.domain.risk_config import RiskConfig
from verasig.features.risk.repository import read_risk_config
from verasig.features.simulation.backtesting import (
    compose_score,
    load_folded_signals,
    persist_result,
    simulate_outcomes,
)
from verasig.features.simulation.schemas import done_out
from verasig.foundation.http.auth_dependencies import require_feed
from verasig.foundation.http.errors import ApiError
from verasig.foundation.http.schemas import JobOut
from verasig.foundation.http.sse import sse_stream, start_job_or_409
from verasig.foundation.jobs.registry import job_key

router = APIRouter(prefix="/feeds/{external_id}")

BACKTEST_PHASES = (
    "Replaying historical signals",
    "Applying your risk model",
    "Simulating fills & slippage",
    "Scoring confidence & drawdown",
)


def _job_key(user_id: UUID, channel_id: int) -> str:
    return job_key(user_id, channel_id, "backtest")


async def _run_backtest_job(
    publisher,
    session_factory,
    user_id: UUID,
    channel_id: int,
    market_data_factory,
    now: datetime,
) -> dict:
    # DB reads/writes, kline fetches and the replay are blocking; each runs in a
    # worker thread so the event loop keeps serving requests and SSE progress.
    publisher.progress({"phase": BACKTEST_PHASES[0]})
    inputs = await asyncio.to_thread(
        load_folded_signals, session_factory, user_id, channel_id
    )
    publisher.progress({"phase": BACKTEST_PHASES[1]})
    risk_config = await asyncio.to_thread(
        _risk_config, session_factory, user_id, channel_id
    )
    publisher.progress({"phase": BACKTEST_PHASES[2]})
    outcomes = await asyncio.to_thread(
        simulate_outcomes, inputs, market_data_factory(), risk_config, now
    )
    publisher.progress({"phase": BACKTEST_PHASES[3]})
    summary = await asyncio.to_thread(compose_score, inputs, outcomes, now)
    await asyncio.to_thread(
        persist_result, session_factory, user_id, channel_id, summary, now
    )
    return done_out(summary).model_dump(by_alias=True)


def _risk_config(session_factory, user_id: UUID, channel_id: int) -> RiskConfig:
    with session_factory() as session:
        return read_risk_config(session, user_id, channel_id) or RiskConfig()


@router.post("/backtest", status_code=status.HTTP_202_ACCEPTED)
async def start_backtest(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
) -> JobOut:
    if subscription.status not in REVIEWED_STATUSES:
        raise ApiError(
            409, "FEED_NOT_VERIFIED", "Feed must be verified before backtesting"
        )
    key = _job_key(subscription.user_id, subscription.external_id)
    start_job_or_409(
        request.app.state.jobs,
        key,
        lambda publisher: _run_backtest_job(
            publisher,
            request.app.state.session_factory,
            subscription.user_id,
            subscription.external_id,
            request.app.state.market_data_factory,
            datetime.now(tz=UTC),
        ),
    )
    return JobOut(job_id=key)


@router.get("/backtest/progress")
def backtest_progress(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
):
    key = _job_key(subscription.user_id, subscription.external_id)
    return sse_stream(request.app.state.jobs, key)
