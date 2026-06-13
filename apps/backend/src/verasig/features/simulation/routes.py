from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from verasig.domain.risk_config import RiskConfig
from verasig.features.risk.repository import read_risk_config
from verasig.features.rules.schemas import JobOut
from verasig.features.simulation.backtesting import (
    compose_score,
    load_folded_signals,
    persist_result,
    simulate_outcomes,
)
from verasig.features.simulation.schemas import done_out
from verasig.foundation.http.auth_dependencies import require_user_channel
from verasig.foundation.http.errors import ApiError
from verasig.foundation.http.sse import sse_stream
from verasig.foundation.jobs.registry import JobAlreadyRunningError

router = APIRouter(prefix="/chats/{chat_id}")

BACKTEST_PHASES = (
    "Replaying historical signals",
    "Applying your risk model",
    "Simulating fills & slippage",
    "Scoring confidence & drawdown",
)


def _job_key(user_id: UUID, channel_id: int) -> str:
    return f"{user_id}:{channel_id}:backtest"


async def _run_backtest_job(
    publisher,
    session_factory,
    user_id: UUID,
    channel_id: int,
    market_data_factory,
    now: datetime,
) -> dict:
    publisher.progress({"phase": BACKTEST_PHASES[0]})
    inputs = load_folded_signals(session_factory, user_id, channel_id)
    publisher.progress({"phase": BACKTEST_PHASES[1]})
    risk_config = _risk_config(session_factory, user_id, channel_id)
    publisher.progress({"phase": BACKTEST_PHASES[2]})
    outcomes = simulate_outcomes(inputs, market_data_factory(), risk_config, now)
    publisher.progress({"phase": BACKTEST_PHASES[3]})
    summary = compose_score(inputs, outcomes, now)
    persist_result(session_factory, user_id, channel_id, summary, now)
    return done_out(summary).model_dump(by_alias=True)


def _risk_config(session_factory, user_id: UUID, channel_id: int) -> RiskConfig:
    with session_factory() as session:
        return read_risk_config(session, user_id, channel_id) or RiskConfig()


@router.post("/backtest", status_code=status.HTTP_202_ACCEPTED)
async def start_backtest(
    request: Request,
    chat_id: str,
    subscription=Depends(require_user_channel),
) -> JobOut:
    key = _job_key(subscription.user_id, int(chat_id))
    try:
        request.app.state.jobs.start(
            key,
            lambda publisher: _run_backtest_job(
                publisher,
                request.app.state.session_factory,
                subscription.user_id,
                int(chat_id),
                request.app.state.market_data_factory,
                datetime.now(tz=UTC),
            ),
        )
    except JobAlreadyRunningError as error:
        raise ApiError(409, "JOB_ALREADY_RUNNING", "Job is already running") from error
    return JobOut(job_id=key)


@router.get("/backtest/progress")
def backtest_progress(
    request: Request,
    chat_id: str,
    subscription=Depends(require_user_channel),
):
    key = _job_key(subscription.user_id, int(chat_id))
    if not request.app.state.jobs.has_job(key):
        raise ApiError(404, "JOB_NOT_FOUND", "Job not found")
    return sse_stream(request.app.state.jobs, key)
