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
streams it, ``GET /mining/result`` reads the cached snapshot.
"""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from verasig.features.feeds import message_repository
from verasig.features.feeds.feed_job_progress import publish_logged_progress
from verasig.features.mining.mine_result_repository import (
    read_mine_result,
    upsert_mine_result,
)
from verasig.features.mining.mining_schemas import MineResultOut
from verasig.features.mining.template_mining import ChatMessage, mine_template_groups
from verasig.features.parser_overlay.repository import read_overlay
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


def _to_chat_message(message) -> ChatMessage:
    return ChatMessage(
        id=str(message.message_id),
        text=message.text or "",
        date=message.posted_at.isoformat() if message.posted_at else None,
    )


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


async def _run_mine(
    publisher: JobPublisher,
    user_id: UUID,
    channel_id: int,
    session_factory,
) -> dict:
    _publish(publisher, channel_id, "loading", 0)
    with session_factory() as session:
        raw_messages = message_repository.read_messages(session, user_id, channel_id)
        overlay = read_overlay(session, user_id)
    messages = [_to_chat_message(message) for message in raw_messages]
    _publish(publisher, channel_id, "extracting", len(messages))
    # CPU-bound pure port — run off the event loop so progress can flush.
    groups = await asyncio.to_thread(mine_template_groups, messages, overlay)
    _publish(publisher, channel_id, "grouping", len(groups))
    # Carry the raw messages too: the browser's verify audit re-runs the parser
    # over the full history (a client-side preview of the server-side confirm).
    out = MineResultOut.model_validate(
        {"groups": groups, "messages": messages}, from_attributes=True
    )
    payload = out.model_dump(by_alias=True, mode="json")
    # Cache the snapshot so reopening a verified feed hydrates Verify from it
    # instead of re-running this scan (see GET /mining/result below).
    with session_factory() as session:
        upsert_mine_result(session, user_id, channel_id, payload)
        session.commit()
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
    """The last cached mine snapshot ({groups, messages}) for this feed — a pure
    read (no re-mine); require_feed 404s a foreign feed. Reopening a verified feed
    hydrates the Verify audit from this instead of re-running the scan; 404 when a
    feed was verified before this cache existed, so the client falls back to a
    live mine."""
    with request.app.state.session_factory() as session:
        payload = read_mine_result(session, subscription.user_id, int(external_id))
    if payload is None:
        raise ApiError(404, "MINE_RESULT_NOT_FOUND", "No cached mine result")
    return payload
