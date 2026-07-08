"""Mining Confirm and Audit endpoints (ADR 0015).

``POST /feeds/{external_id}/mining/confirm`` persists the accepted template
families' signals (miner-based) and marks the feed verified. Sync handler: the
re-mining is CPU-bound and runs in FastAPI's threadpool. Blocked while a backfill
runs, so capture and confirm never race on the same feed.

``POST /feeds/{external_id}/mining/audit`` is the server-side twin of the
browser's Verify audit: re-mine the feed, keep the accepted families, run them
over every stored message, and return the SAME camelCase audit shape the
browser used to compute client-side (parsedSignals / ambiguousCandidates /
rejectedCandidates / rareTemplates / potentialMisses). A pure read — it never
touches the feed status or persisted signals; only Confirm does that.
"""

import logging

from fastapi import APIRouter, Depends, Request

from verasig.domain.feed import FeedStatus
from verasig.features.feeds.backfill_job_run import backfill_job_key
from verasig.features.mining.mining_audit import compute_audit
from verasig.features.mining.mining_confirm import (
    MiningConfirmResult,
    confirm_mined_signals,
    mine_feed_messages,
    read_confirmed_template_keys,
)
from verasig.features.mining.mining_schemas import (
    MiningAuditIn,
    MiningAuditOut,
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
    if feed.status == FeedStatus.BACKFILLING or request.app.state.jobs.has_job(key):
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


@router.post("/audit")
def mining_audit(
    request: Request,
    external_id: str,
    payload: MiningAuditIn,
    feed=Depends(require_feed),
) -> MiningAuditOut:
    """Re-mine the feed, keep the accepted families, and run them over every
    stored message — a pure read (no persistence, no backfill guard); require_feed
    404s a foreign feed."""
    messages, groups, overlay = mine_feed_messages(
        request.app.state.session_factory, feed.user_id, int(external_id)
    )
    audit = compute_audit(messages, groups, payload.accepted_template_keys, overlay)
    return MiningAuditOut.model_validate(audit, from_attributes=True)
