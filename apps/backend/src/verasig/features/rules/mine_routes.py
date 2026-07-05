"""Mine endpoints: run the template miner as a background job with SSE progress.

Mirrors the shared job pattern (see the backfill/deletion-rescan jobs): POST
starts a one-shot mining job on `app.state.jobs`; GET streams its staged progress
and terminal result over SSE. The miner is a pure, deterministic port of the
frontend template-mining module — this module only loads the feed's messages,
drives progress, and serializes the mined template families for the browser to
review. No LLM.
"""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from verasig.features.feeds import message_repository
from verasig.features.feeds.feed_job_progress import publish_logged_progress
from verasig.features.parser_overlay.repository import read_overlay
from verasig.features.rules.schemas import JobOut
from verasig.features.rules.template_mining import (
    ChatMessage,
    mine_template_groups,
    template_group_to_dict,
)
from verasig.foundation.http.auth_dependencies import require_feed
from verasig.foundation.http.errors import ApiError
from verasig.foundation.http.sse import sse_stream
from verasig.foundation.jobs.registry import (
    JobAlreadyRunningError,
    JobPublisher,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feeds/{external_id}")

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


def _to_camel(snake: str) -> str:
    head, *rest = snake.split("_")
    return head + "".join(word[:1].upper() + word[1:] for word in rest)


# The browser consumes the miner's JS camelCase shape. One exception:
# intentDistribution's inner keys are a fixed enum read verbatim (new_signal, …),
# so camelize that key but leave its value's keys untouched.
_PRESERVE_VALUE_KEYS = {"intent_distribution"}


def _camelize(value):
    if isinstance(value, dict):
        return {
            _to_camel(key): inner if key in _PRESERVE_VALUE_KEYS else _camelize(inner)
            for key, inner in value.items()
        }
    if isinstance(value, list):
        return [_camelize(item) for item in value]
    return value


def mine_job_key(user_id: UUID, channel_id: int) -> str:
    return f"{user_id}:{channel_id}:mine"


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
    payload = {
        "groups": [_camelize(template_group_to_dict(group)) for group in groups],
        "messages": [
            {"id": message.id, "text": message.text, "date": message.date}
            for message in messages
        ],
    }
    _publish(publisher, channel_id, "complete", len(groups))
    return payload


@router.post("/mine", status_code=status.HTTP_202_ACCEPTED)
async def start_mine(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
) -> JobOut:
    channel_id = int(external_id)
    key = mine_job_key(subscription.user_id, channel_id)
    try:
        request.app.state.jobs.start(
            key,
            lambda publisher: _run_mine(
                publisher,
                subscription.user_id,
                channel_id,
                request.app.state.session_factory,
            ),
        )
    except JobAlreadyRunningError as error:
        raise ApiError(409, "JOB_ALREADY_RUNNING", "Job is already running") from error
    return JobOut(job_id=key)


@router.get("/mine/progress")
def mine_progress(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
):
    key = mine_job_key(subscription.user_id, int(external_id))
    if not request.app.state.jobs.has_job(key):
        raise ApiError(404, "JOB_NOT_FOUND", "Job not found")
    return sse_stream(request.app.state.jobs, key)
