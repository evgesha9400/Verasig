from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from verasig.api.deps import get_current_user
from verasig.api.errors import ApiError
from verasig.api.schemas.signal import LinkModIn
from verasig.domain.account import UserAccount
from verasig.services.projection.signals import (
    link_modifier,
    present_signal,
    present_signals,
)

router = APIRouter(prefix="/signals")


@router.get("")
def list_signals(
    request: Request,
    feed_id: str | None = Query(None, alias="feedId"),
    status: str | None = None,
    user: UserAccount = Depends(get_current_user),
) -> dict:
    with request.app.state.session_factory() as session:
        return present_signals(session, user.id, feed_id, status, user.plan)


@router.get("/{signal_id}")
def get_signal(
    request: Request,
    signal_id: UUID,
    user: UserAccount = Depends(get_current_user),
) -> dict:
    with request.app.state.session_factory() as session:
        signal = present_signal(session, user.id, signal_id)
    if signal is None:
        raise ApiError(404, "SIGNAL_NOT_FOUND", "Signal not found")
    return signal


@router.post("/{signal_id}/link-mod")
def link_mod(
    request: Request,
    signal_id: UUID,
    payload: LinkModIn,
    user: UserAccount = Depends(get_current_user),
) -> dict:
    with request.app.state.session_factory() as session:
        signal = link_modifier(session, user.id, signal_id, payload.mod_id)
        if signal is None:
            raise ApiError(404, "SIGNAL_NOT_FOUND", "Signal not found")
        session.commit()
        return signal
