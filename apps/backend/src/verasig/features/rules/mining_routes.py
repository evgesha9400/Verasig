"""Mining Confirm endpoint (ADR 0015).

`POST /feeds/{external_id}/mining/rules` persists the browser-compiled ruleset
and re-derives extraction + evidence + status. Sync handler: the re-derivation
is CPU-bound and runs in FastAPI's threadpool. Blocked while a backfill runs, so
capture and re-derivation never race on the same feed.
"""

import logging

from fastapi import APIRouter, Depends, Request

from verasig.features.feeds.backfill_job_run import backfill_job_key
from verasig.features.rules.mining_confirm import (
    MiningConfirmResult,
    confirm_mining_rules,
)
from verasig.features.rules.mining_schemas import MiningRulesConfirmIn
from verasig.foundation.http.auth_dependencies import require_feed
from verasig.foundation.http.errors import ApiError
from verasig.foundation.market_data.static_exchange import StaticExchange

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


def _present(result: MiningConfirmResult) -> dict:
    return {
        "version": result.version,
        "filterRuleId": result.filter_rule_id,
        "parserRuleIds": result.parser_rule_ids,
        "pipeline": {
            "candidatesCreated": result.candidates_created,
            "parserRecovered": result.parser_recovered,
            "signalsExtracted": result.signals_extracted,
            "unrecognized": result.unrecognized,
            "evidenceUpdated": result.evidence_updated,
        },
        "feedStatus": result.feed_status,
    }


@router.post("/rules")
def confirm_rules(
    request: Request,
    external_id: str,
    payload: MiningRulesConfirmIn,
    feed=Depends(require_feed),
) -> dict:
    _guard_not_backfilling(request, feed)
    result = confirm_mining_rules(
        request.app.state.session_factory,
        feed.user_id,
        int(external_id),
        payload.filter_rule,
        payload.parser_rules,
        StaticExchange(),
    )
    return _present(result)
