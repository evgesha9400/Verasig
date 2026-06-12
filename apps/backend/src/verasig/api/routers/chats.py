from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response, status

from verasig.api.deps import get_current_user, require_user_channel
from verasig.api.errors import ApiError
from verasig.api.schemas.chat import ChatCreateIn
from verasig.domain.account import UserAccount
from verasig.foundation.telegram_session import make_user_source
from verasig.services.accounts.plans import require_source_capacity
from verasig.services.projection.chats import present_chats
from verasig.storage import repositories as repo
from verasig.storage.telegram_link_repository import read_link
from verasig.storage.user_channel_repository import subscribe, unsubscribe

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
