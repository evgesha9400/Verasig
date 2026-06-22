from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from verasig.domain.account import UserAccount
from verasig.features.signals.schemas import LinkModIn
from verasig.features.signals.views import (
    link_modifier,
    present_signal,
    present_signals,
)
from verasig.foundation.http.auth_dependencies import get_current_user
from verasig.foundation.http.errors import ApiError

router = APIRouter(prefix="/signals")


@router.get("")
def list_signals(
    request: Request,
    feed_id: str | None = Query(None, alias="feedId"),
    status: str | None = None,
    user: UserAccount = Depends(get_current_user),
) -> dict:
    with request.app.state.session_factory() as session:
        result = present_signals(session, user.id, feed_id, status, user.plan)
        session.commit()
        return result


@router.get("/{signal_id}")
def get_signal(
    request: Request,
    signal_id: UUID,
    user: UserAccount = Depends(get_current_user),
) -> dict:
    with request.app.state.session_factory() as session:
        signal = present_signal(session, user.id, signal_id)
        session.commit()
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
