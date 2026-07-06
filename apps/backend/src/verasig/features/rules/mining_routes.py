"""Mining Confirm endpoint (ADR 0015).

``POST /feeds/{external_id}/mining/confirm`` persists the accepted template
families' signals (miner-based) and marks the feed verified. Sync handler: the
re-mining is CPU-bound and runs in FastAPI's threadpool. Blocked while a backfill
runs, so capture and confirm never race on the same feed.
"""

import logging

from fastapi import APIRouter, Depends, Request

from verasig.features.feeds.backfill_job_run import backfill_job_key
from verasig.features.rules.mining_confirm import (
    MiningConfirmResult,
    confirm_mined_signals,
    read_confirmed_template_keys,
)
from verasig.features.rules.mining_schemas import (
    MiningConfirmedOut,
    MiningConfirmIn,
    MiningConfirmOut,
)
from verasig.foundation.http.auth_dependencies import require_feed
from verasig.foundation.http.errors import ApiError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feeds/{external_id}/mining")


def _guard_not_backfilling(request: Request, feed) -> None:
    key = backfill_job_key(feed.user_id, feed.external_id)
    if feed.status == "backfilling" or request.app.state.jobs.has_job(key):
        raise ApiError(
            409,
            "MINING_CONFIRM_CONFLICT",
            "A backfill is running for this feed; confirm again once it finishes.",
        )


def _present(result: MiningConfirmResult) -> MiningConfirmOut:
    return MiningConfirmOut(
        feed_status=result.feed_status,
        templates_accepted=result.templates_accepted,
        signals_extracted=result.signals_extracted,
    )


@router.post("/confirm")
def confirm_signals(
    request: Request,
    external_id: str,
    payload: MiningConfirmIn,
    feed=Depends(require_feed),
) -> MiningConfirmOut:
    _guard_not_backfilling(request, feed)
    result = confirm_mined_signals(
        request.app.state.session_factory,
        feed.user_id,
        int(external_id),
        payload.accepted_template_keys,
    )
    return _present(result)


@router.get("/confirmed")
def read_confirmed(
    request: Request,
    external_id: str,
    feed=Depends(require_feed),
) -> MiningConfirmedOut:
    """List the accepted template keys already persisted for this feed — a pure
    read (no re-mine, no backfill guard); require_feed 404s a foreign feed."""
    keys = read_confirmed_template_keys(
        request.app.state.session_factory,
        feed.user_id,
        int(external_id),
    )
    return MiningConfirmedOut(accepted_template_keys=keys)
