"""Mining Confirm and Audit endpoints (ADR 0015).

``POST /feeds/{external_id}/mining/confirm`` validates a MiningReview, persists
the accepted template families' signals from that exact snapshot, and marks the
feed verified. The feed row lock serializes confirm with backfill.

``POST /feeds/{external_id}/mining/audit`` is the server-side twin of the
browser's Verify audit: validate the supplied review, keep the accepted families,
and run them over its exact stored messages. It returns the same camelCase audit
shape the browser used to compute client-side (parsedSignals /
ambiguousCandidates / rejectedCandidates / rareTemplates / potentialMisses).
"""

import logging

from fastapi import APIRouter, Depends, Request

from verasig.features.mining.mining_audit import compute_audit
from verasig.features.mining.mining_confirm import (
    MiningConfirmConflictError,
    MiningConfirmResult,
    confirm_review,
    read_confirmed_template_keys,
)
from verasig.features.mining.mining_review import (
    MiningReviewNotFoundError,
    MiningReviewStaleError,
    require_current_review,
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
    try:
        result = confirm_review(
            request.app.state.session_factory,
            feed.user_id,
            int(external_id),
            payload.review_id,
            payload.accepted_template_keys,
        )
    except MiningReviewNotFoundError as error:
        raise ApiError(404, "MINING_REVIEW_NOT_FOUND", str(error)) from error
    except MiningReviewStaleError as error:
        raise ApiError(409, "MINING_REVIEW_STALE", str(error)) from error
    except MiningConfirmConflictError as error:
        raise ApiError(409, "MINING_CONFIRM_CONFLICT", str(error)) from error
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
    """Audit the exact current review snapshot without persisting changes."""
    with request.app.state.session_factory() as session:
        try:
            review = require_current_review(
                session,
                feed.user_id,
                int(external_id),
                payload.review_id,
            )
        except MiningReviewNotFoundError as error:
            raise ApiError(404, "MINING_REVIEW_NOT_FOUND", str(error)) from error
        except MiningReviewStaleError as error:
            raise ApiError(409, "MINING_REVIEW_STALE", str(error)) from error
    audit = compute_audit(
        review.messages,
        review.groups,
        payload.accepted_template_keys,
        review.overlay,
    )
    return MiningAuditOut.model_validate(audit, from_attributes=True)
