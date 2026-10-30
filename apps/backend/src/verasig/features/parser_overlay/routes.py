from fastapi import APIRouter, Depends, Request

from verasig.domain.account import UserAccount
from verasig.features.parser_overlay.repository import read_overlay, upsert_overlay
from verasig.features.parser_overlay.schemas import ParserOverlayBody, ParserOverlayData
from verasig.foundation.http.auth_dependencies import get_current_user

router = APIRouter(prefix="/parser-overlay")


@router.get("")
def get_overlay(
    request: Request, user: UserAccount = Depends(get_current_user)
) -> ParserOverlayBody:
    with request.app.state.session_factory() as session:
        config = read_overlay(session, user.id)
    return ParserOverlayBody(overlay=ParserOverlayData(**config))


@router.put("")
def put_overlay(
    request: Request,
    payload: ParserOverlayBody,
    user: UserAccount = Depends(get_current_user),
) -> ParserOverlayBody:
    config = payload.overlay.model_dump(by_alias=True)
    with request.app.state.session_factory() as session:
        upsert_overlay(session, user.id, config)
        session.commit()
    return payload
