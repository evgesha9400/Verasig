"""Mine (preview) endpoints: run the template miner as a background job with SSE
progress.

Mirrors the shared job pattern (see the backfill/deletion-rescan jobs): POST
starts a one-shot mining job on `app.state.jobs`; GET streams its staged progress
and terminal result over SSE. The miner is a pure, deterministic port of the
frontend template-mining module — this module only loads the feed's messages,
drives progress, and serializes the mined template families for the browser to
review. No LLM.

Mounted under the same ``/mining`` prefix as ``mining_routes`` (confirm/confirmed/
audit): ``POST /mining/preview`` starts the scan, ``GET /mining/preview/progress``
streams it, and ``GET /mining/result`` reads the latest current review.
"""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from verasig.features.feeds.feed_job_progress import publish_logged_progress
from verasig.features.mining.mining_review import (
    MiningReview,
    MiningReviewInput,
    MiningReviewNotFoundError,
    MiningReviewStaleError,
    create_review,
    read_input,
    require_latest_current_review,
)
from verasig.features.mining.mining_schemas import MineResultOut
from verasig.features.mining.template_mining import mine_template_groups
from verasig.foundation.http.auth_dependencies import require_feed
from verasig.foundation.http.errors import ApiError
from verasig.foundation.http.schemas import JobOut
from verasig.foundation.http.sse import sse_stream, start_job_or_409
from verasig.foundation.jobs.registry import JobPublisher, job_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feeds/{external_id}/mining")

# Coarse, ordered stages the UI shows as a progress strip (like backfill's).
MINE_STAGES = (
    ("loading", "Loading message history"),
    ("extracting", "Extracting signal candidates"),
    ("grouping", "Grouping into template families"),
    ("complete", "Mining complete"),
)
MINE_TOTAL_STEPS = len(MINE_STAGES)
MINE_STAGE_BY_KEY = {
    stage: {"phase": phase, "step": index}
    for index, (stage, phase) in enumerate(MINE_STAGES, start=1)
}


def mine_job_key(user_id: UUID, channel_id: int) -> str:
    return job_key(user_id, channel_id, "mine")


def _progress_payload(stage: str, count: int) -> dict:
    definition = MINE_STAGE_BY_KEY[stage]
    return {
        "stage": stage,
        "phase": definition["phase"],
        "step": definition["step"],
        "totalSteps": MINE_TOTAL_STEPS,
        "count": count,
    }


def _publish(publisher: JobPublisher, channel_id: int, stage: str, count: int) -> None:
    payload = _progress_payload(stage, count)
    publish_logged_progress(
        publisher,
        payload,
        logger=logger,
        operation="mine",
        external_id=channel_id,
        phase=payload["phase"],
        stage=stage,
        step=payload["step"],
        total_steps=payload["totalSteps"],
        count=count,
    )


def _load_input(session_factory, user_id: UUID, channel_id: int) -> MiningReviewInput:
    with session_factory() as session:
        return read_input(session, user_id, channel_id)


def _persist_review(
    session_factory,
    user_id: UUID,
    channel_id: int,
    review_input: MiningReviewInput,
    groups: list,
) -> dict:
    with session_factory() as session:
        review = create_review(session, user_id, channel_id, review_input, groups)
        session.commit()
    return _mine_result_payload(review)


def _mine_result_payload(review: MiningReview) -> dict:
    return MineResultOut.model_validate(
        {
            "review_id": review.review_id,
            "input_revision": review.input_revision,
            "groups": review.groups,
            "messages": review.messages,
            "total_messages": len(review.messages),
        },
        from_attributes=True,
    ).model_dump(by_alias=True, mode="json")


async def _run_mine(
    publisher: JobPublisher,
    user_id: UUID,
    channel_id: int,
    session_factory,
) -> dict:
    # DB reads/writes and the CPU-bound pure miner all run off the event loop,
    # so other requests and the SSE progress keep flowing.
    _publish(publisher, channel_id, "loading", 0)
    review_input = await asyncio.to_thread(
        _load_input, session_factory, user_id, channel_id
    )
    _publish(publisher, channel_id, "extracting", len(review_input.messages))
    groups = await asyncio.to_thread(
        mine_template_groups, review_input.messages, review_input.overlay
    )
    _publish(publisher, channel_id, "grouping", len(groups))
    payload = await asyncio.to_thread(
        _persist_review, session_factory, user_id, channel_id, review_input, groups
    )
    _publish(publisher, channel_id, "complete", len(groups))
    return payload


@router.post("/preview", status_code=status.HTTP_202_ACCEPTED)
async def start_mine(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
) -> JobOut:
    channel_id = int(external_id)
    key = mine_job_key(subscription.user_id, channel_id)
    start_job_or_409(
        request.app.state.jobs,
        key,
        lambda publisher: _run_mine(
            publisher,
            subscription.user_id,
            channel_id,
            request.app.state.session_factory,
        ),
    )
    return JobOut(job_id=key)


@router.get("/preview/progress")
def mine_progress(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
):
    key = mine_job_key(subscription.user_id, int(external_id))
    return sse_stream(request.app.state.jobs, key)


@router.get("/result")
def mine_result(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
) -> dict:
    """Read the latest current MiningReview for this feed without re-mining."""
    with request.app.state.session_factory() as session:
        try:
            review = require_latest_current_review(
                session, subscription.user_id, int(external_id)
            )
        except MiningReviewNotFoundError:
            review = None
        except MiningReviewStaleError as error:
            raise ApiError(409, "MINING_REVIEW_STALE", str(error)) from error
    if review is None:
        raise ApiError(404, "MINE_RESULT_NOT_FOUND", "No current mining review")
    return _mine_result_payload(review)
