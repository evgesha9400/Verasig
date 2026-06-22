import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response, status

from verasig.domain.account import UserAccount
from verasig.domain.channel_reference import ChannelReferenceResolutionError
from verasig.features.accounts.plans import (
    PlanSourceLimitExceeded,
    require_source_capacity,
)
from verasig.features.feeds import (
    feed_repository,
)
from verasig.features.feeds.backfill_job_run import (
    BackfillMode,
    backfill_job_key,
    present_progress,
    progress_event_name,
)
from verasig.features.feeds.deletion_rescan import RescanAborted, RescanResult, rescan
from verasig.features.feeds.feed_job_progress import (
    publish_logged_progress,
    scan_phase,
    should_publish_count,
)
from verasig.features.feeds.feed_views import present_feeds
from verasig.features.feeds.schemas import BackfillStartIn, FeedCreateIn
from verasig.features.sources.telegram_adapter import read_connection
from verasig.foundation.http.auth_dependencies import (
    get_current_user,
    require_feed,
)
from verasig.foundation.http.errors import ApiError
from verasig.foundation.http.sse import sse_single_event, sse_stream
from verasig.foundation.jobs.registry import JobAlreadyRunningError, JobTerminalError
from verasig.foundation.telegram.session import make_user_source

router = APIRouter(prefix="/feeds")
logger = logging.getLogger(__name__)

DELETION_RESCAN_READY_STATUSES = {"verified", "analyzed"}
DELETION_RESCAN_PROGRESS_INTERVAL = 200


def _resolve_source(request: Request, connection):
    factory = getattr(request.app.state, "telegram_source_factory", None)
    if factory is not None:
        return factory(connection)
    return make_user_source(
        connection.config["session_string"],
        connection.config["api_id"],
        connection.config["api_hash"],
    )


def _require_connected_source(request: Request, session, user_id):
    connection = read_connection(session, user_id, request.app.state.secret_cipher)
    if connection is None or connection.status != "connected":
        raise ApiError(409, "TELEGRAM_NOT_CONNECTED", "Telegram is not connected")
    return _resolve_source(request, connection)


@router.get("")
def list_feeds(request: Request, user: UserAccount = Depends(get_current_user)) -> dict:
    request.app.state.backfill_jobs.mark_inactive_backfilling_failed(user.id)
    with request.app.state.session_factory() as session:
        return {"feeds": present_feeds(session, user.id)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_feed(
    request: Request,
    payload: FeedCreateIn,
    user: UserAccount = Depends(get_current_user),
) -> dict:
    with request.app.state.session_factory() as session:
        try:
            require_source_capacity(user, session)
        except PlanSourceLimitExceeded as error:
            raise ApiError(403, "PLAN_LIMIT_SOURCES", "Source limit reached") from error
        source = _require_connected_source(request, session, user.id)
        try:
            async with source:
                channel = await source.resolve_channel(payload.tag)
        except ChannelReferenceResolutionError as error:
            raise ApiError(404, "CHANNEL_NOT_FOUND", str(error)) from error
        feed_repository.create_feed(session, user.id, channel, datetime.now(tz=UTC))
        session.commit()
        feeds = present_feeds(session, user.id)
    return next(feed for feed in feeds if feed["id"] == str(channel.channel_id))


@router.delete("/{external_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feed(
    request: Request,
    external_id: str,
    _subscription=Depends(require_feed),
) -> Response:
    with request.app.state.session_factory() as session:
        feed_repository.delete_feed(session, _subscription.user_id, int(external_id))
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{external_id}/backfill", status_code=status.HTTP_202_ACCEPTED)
async def start_backfill(
    request: Request,
    external_id: str,
    payload: BackfillStartIn | None = None,
    subscription=Depends(require_feed),
) -> dict:
    channel_id = int(external_id)
    mode = payload.mode if payload else BackfillMode.RESUME

    def make_source():
        with request.app.state.session_factory() as session:
            return _require_connected_source(request, session, subscription.user_id)

    run = request.app.state.backfill_jobs.start(
        subscription.user_id, channel_id, make_source, mode
    )
    return {"jobId": str(run.id)}


@router.post("/{external_id}/backfill/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_backfill(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
) -> Response:
    request.app.state.backfill_jobs.cancel(subscription.user_id, int(external_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _deletion_rescan_job_key(user_id, external_id: int) -> str:
    return f"{user_id}:{external_id}:deletion-rescan"


def _require_deletion_rescan_ready(feed) -> None:
    if feed.status in DELETION_RESCAN_READY_STATUSES:
        return
    raise ApiError(
        409,
        "DELETION_RESCAN_NOT_READY",
        "Check gaps is available after feed verification.",
    )


def _present_deletion_rescan_result(result: RescanResult) -> dict:
    return {
        "externalId": str(result.external_id),
        "newDeletedSignalCount": result.new_deleted_signal_count,
        "newDeletedNonSignalCount": result.new_deleted_non_signal_count,
        "newSuspectedGapCount": result.new_suspected_gap_count,
        "totalDeletedCount": result.total_deleted_count,
        "signalDeletion": result.signal_deletion,
    }


def _publish_deletion_rescan_progress(
    publisher, external_id: int, scanned: int
) -> None:
    phase = scan_phase(scanned)
    publish_logged_progress(
        publisher,
        {
            "phase": phase,
            "scanned": scanned,
        },
        logger=logger,
        operation="deletion_rescan",
        external_id=external_id,
        phase=phase,
        scanned=scanned,
    )


def _publish_deletion_rescan_phase(publisher, external_id: int, phase: str) -> None:
    publish_logged_progress(
        publisher,
        {"phase": phase},
        logger=logger,
        operation="deletion_rescan",
        external_id=external_id,
        phase=phase,
    )


def _deletion_rescan_progress_reporter(publisher, external_id: int):
    def report(scanned: int) -> None:
        if should_publish_count(scanned, DELETION_RESCAN_PROGRESS_INTERVAL):
            _publish_deletion_rescan_progress(publisher, external_id, scanned)

    return report


async def _run_deletion_rescan_job(
    publisher,
    source,
    user_id,
    external_id: int,
    session_factory,
) -> dict:
    _publish_deletion_rescan_phase(publisher, external_id, "Opening MTProto session...")
    try:
        async with source:
            _publish_deletion_rescan_progress(publisher, external_id, 0)
            result = await rescan(
                source,
                user_id,
                external_id,
                session_factory,
                on_progress=_deletion_rescan_progress_reporter(publisher, external_id),
            )
    except RescanAborted as error:
        raise JobTerminalError(
            str(error),
            {
                "code": "EMPTY_LIVE_SNAPSHOT",
                "message": str(error),
            },
        ) from error
    return _present_deletion_rescan_result(result)


@router.post("/{external_id}/deletion-rescan", status_code=status.HTTP_202_ACCEPTED)
async def start_deletion_rescan(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
) -> dict:
    channel_id = int(external_id)
    _require_deletion_rescan_ready(subscription)

    with request.app.state.session_factory() as session:
        source = _require_connected_source(request, session, subscription.user_id)

    key = _deletion_rescan_job_key(subscription.user_id, channel_id)
    try:
        request.app.state.jobs.start(
            key,
            lambda publisher: _run_deletion_rescan_job(
                publisher,
                source,
                subscription.user_id,
                channel_id,
                request.app.state.session_factory,
            ),
        )
    except JobAlreadyRunningError as error:
        raise ApiError(409, "JOB_ALREADY_RUNNING", "Job is already running") from error
    return {"jobId": key}


@router.get("/{external_id}/deletion-rescan/progress")
def deletion_rescan_progress(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
):
    key = _deletion_rescan_job_key(subscription.user_id, int(external_id))
    if not request.app.state.jobs.has_job(key):
        raise ApiError(404, "JOB_NOT_FOUND", "Job not found")
    return sse_stream(request.app.state.jobs, key)


@router.get("/{external_id}/backfill/progress")
def backfill_progress(
    request: Request,
    external_id: str,
    subscription=Depends(require_feed),
):
    channel_id = int(external_id)
    request.app.state.backfill_jobs.mark_inactive_backfilling_failed(
        subscription.user_id, channel_id
    )
    key = backfill_job_key(subscription.user_id, channel_id)
    if request.app.state.jobs.has_job(key):
        return sse_stream(request.app.state.jobs, key)
    progress = request.app.state.backfill_jobs.read_progress(
        subscription.user_id, channel_id
    )
    if progress is None:
        raise ApiError(404, "JOB_NOT_FOUND", "Job not found")
    return sse_single_event(progress_event_name(progress), present_progress(progress))
