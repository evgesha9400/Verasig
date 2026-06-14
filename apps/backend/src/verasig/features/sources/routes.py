from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response, status

from verasig.domain.account import UserAccount
from verasig.domain.channel_reference import ChannelReferenceResolutionError
from verasig.features.accounts.plans import (
    PlanSourceLimitExceeded,
    require_source_capacity,
)
from verasig.features.sources import (
    channel_repository,
)
from verasig.features.sources.backfill_job_run import (
    backfill_job_key,
    present_progress,
    progress_event_name,
)
from verasig.features.sources.chat_views import present_chats
from verasig.features.sources.schemas import ChatCreateIn
from verasig.features.sources.subscription_repository import (
    subscribe,
    unsubscribe,
)
from verasig.features.telegram_links.repository import read_link
from verasig.foundation.http.auth_dependencies import (
    get_current_user,
    require_user_channel,
)
from verasig.foundation.http.errors import ApiError
from verasig.foundation.http.sse import sse_single_event, sse_stream
from verasig.foundation.telegram.session import make_user_source

router = APIRouter(prefix="/chats")


def _resolve_source(request: Request, link):
    factory = getattr(request.app.state, "telegram_source_factory", None)
    if factory is not None:
        return factory(link)
    cipher = request.app.state.secret_cipher
    aad = f"{link.user_id}:telegram_link"
    return make_user_source(
        cipher.decrypt(link.session_string_encrypted, aad),
        link.api_id,
        cipher.decrypt(link.api_hash_encrypted, aad),
    )


@router.get("")
def list_chats(request: Request, user: UserAccount = Depends(get_current_user)) -> dict:
    request.app.state.backfill_jobs.mark_inactive_backfilling_failed(user.id)
    with request.app.state.session_factory() as session:
        return {"chats": present_chats(session, user.id)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_chat(
    request: Request,
    payload: ChatCreateIn,
    user: UserAccount = Depends(get_current_user),
) -> dict:
    with request.app.state.session_factory() as session:
        try:
            require_source_capacity(user, session)
        except PlanSourceLimitExceeded as error:
            raise ApiError(403, "PLAN_LIMIT_SOURCES", "Source limit reached") from error
        link = read_link(session, user.id)
        if link is None or link.status != "connected":
            raise ApiError(409, "TELEGRAM_NOT_CONNECTED", "Telegram is not connected")
        source = _resolve_source(request, link)
        try:
            async with source:
                channel = await source.resolve_channel(payload.tag)
        except ChannelReferenceResolutionError as error:
            raise ApiError(404, "CHANNEL_NOT_FOUND", str(error)) from error
        channel_repository.upsert_channel(session, channel)
        subscribe(session, user.id, channel.channel_id, datetime.now(tz=UTC))
        session.commit()
        chats = present_chats(session, user.id)
    return next(chat for chat in chats if chat["id"] == str(channel.channel_id))


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    request: Request,
    chat_id: str,
    _subscription=Depends(require_user_channel),
) -> Response:
    with request.app.state.session_factory() as session:
        unsubscribe(session, _subscription.user_id, int(chat_id))
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{chat_id}/backfill", status_code=status.HTTP_202_ACCEPTED)
async def start_backfill(
    request: Request,
    chat_id: str,
    subscription=Depends(require_user_channel),
) -> dict:
    channel_id = int(chat_id)

    def make_source():
        with request.app.state.session_factory() as session:
            link = read_link(session, subscription.user_id)
            if link is None or link.status != "connected":
                raise ApiError(
                    409, "TELEGRAM_NOT_CONNECTED", "Telegram is not connected"
                )
            return _resolve_source(request, link)

    run = request.app.state.backfill_jobs.start(
        subscription.user_id, channel_id, make_source
    )
    return {"jobId": str(run.id)}


@router.post("/{chat_id}/backfill/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_backfill(
    request: Request,
    chat_id: str,
    subscription=Depends(require_user_channel),
) -> Response:
    request.app.state.backfill_jobs.cancel(subscription.user_id, int(chat_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{chat_id}/backfill/progress")
def backfill_progress(
    request: Request,
    chat_id: str,
    subscription=Depends(require_user_channel),
):
    channel_id = int(chat_id)
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
