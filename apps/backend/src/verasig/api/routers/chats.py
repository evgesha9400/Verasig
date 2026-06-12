import itertools
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response, status

from verasig.api.deps import get_current_user, require_user_channel
from verasig.api.errors import ApiError
from verasig.api.schemas.chat import ChatCreateIn
from verasig.api.sse import sse_stream
from verasig.domain.account import UserAccount
from verasig.foundation.static_exchange import StaticExchange
from verasig.foundation.telegram_session import make_user_source
from verasig.services.accounts.plans import require_source_capacity
from verasig.services.deletion.rescan import rescan
from verasig.services.ingestion.backfill import backfill
from verasig.services.ingestion.candidate_derivation import derive_candidates
from verasig.services.jobs.registry import JobAlreadyRunningError
from verasig.services.projection.chats import present_chats
from verasig.services.projection.dates import format_long
from verasig.storage import repositories as repo
from verasig.storage.telegram_link_repository import read_link
from verasig.storage.user_channel_repository import set_status, subscribe, unsubscribe

router = APIRouter(prefix="/chats")

BACKFILL_PHASES = (
    "Opening MTProto session…",
    "Reading channel history…",
    "Decrypting message batch…",
    "Resolving media references…",
    "Backfilling older window…",
    "Indexing message bodies…",
)


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


def _job_key(user_id, channel_id: int, kind: str) -> str:
    return f"{user_id}:{channel_id}:{kind}"


async def _run_backfill(
    publisher,
    source,
    user_id,
    channel_id: int,
    session_factory,
    settings,
) -> dict:
    phases = itertools.cycle(BACKFILL_PHASES)

    def on_batch(fetched: int, oldest) -> None:
        publisher.progress(
            {"fetched": fetched, "lastDate": format_long(oldest), "phase": next(phases)}
        )

    result = await backfill(
        source,
        channel_id,
        session_factory,
        settings.backfill_batch_size,
        on_batch=on_batch,
    )
    derive_candidates(session_factory, channel_id, StaticExchange())
    await rescan(source, channel_id, session_factory)
    with session_factory() as session:
        set_status(session, user_id, channel_id, "backfilled")
        session.commit()
    return {"fetched": result.inserted}


@router.get("")
def list_chats(request: Request, user: UserAccount = Depends(get_current_user)) -> dict:
    with request.app.state.session_factory() as session:
        return {"chats": present_chats(session, user.id)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_chat(
    request: Request,
    payload: ChatCreateIn,
    user: UserAccount = Depends(get_current_user),
) -> dict:
    with request.app.state.session_factory() as session:
        require_source_capacity(user, session)
        link = read_link(session, user.id)
        if link is None or link.status != "connected":
            raise ApiError(409, "TELEGRAM_NOT_CONNECTED", "Telegram is not connected")
        source = _resolve_source(request, link)
        channel = await source.resolve_channel(payload.tag)
        repo.upsert_channel(session, channel)
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
    if subscription.status == "backfilling":
        raise ApiError(409, "JOB_ALREADY_RUNNING", "Job is already running")
    with request.app.state.session_factory() as session:
        link = read_link(session, subscription.user_id)
        if link is None or link.status != "connected":
            raise ApiError(409, "TELEGRAM_NOT_CONNECTED", "Telegram is not connected")
        source = _resolve_source(request, link)
        set_status(session, subscription.user_id, int(chat_id), "backfilling")
        session.commit()
    key = _job_key(subscription.user_id, int(chat_id), "backfill")
    try:
        request.app.state.jobs.start(
            key,
            lambda publisher: _run_backfill(
                publisher,
                source,
                subscription.user_id,
                int(chat_id),
                request.app.state.session_factory,
                request.app.state.settings,
            ),
        )
    except JobAlreadyRunningError as error:
        raise ApiError(409, "JOB_ALREADY_RUNNING", "Job is already running") from error
    return {"jobId": key}


@router.post("/{chat_id}/backfill/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_backfill(
    request: Request,
    chat_id: str,
    subscription=Depends(require_user_channel),
) -> Response:
    request.app.state.jobs.cancel(
        _job_key(subscription.user_id, int(chat_id), "backfill")
    )
    with request.app.state.session_factory() as session:
        set_status(session, subscription.user_id, int(chat_id), "cancelled")
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{chat_id}/backfill/progress")
def backfill_progress(
    request: Request,
    chat_id: str,
    subscription=Depends(require_user_channel),
):
    key = _job_key(subscription.user_id, int(chat_id), "backfill")
    try:
        return sse_stream(request.app.state.jobs, key)
    except KeyError as error:
        raise ApiError(404, "JOB_NOT_FOUND", "Job not found") from error
