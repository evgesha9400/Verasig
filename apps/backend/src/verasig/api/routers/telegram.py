from fastapi import APIRouter, Depends, Request, Response, status

from verasig.api.deps import get_current_user
from verasig.api.errors import ApiError
from verasig.api.schemas.telegram import (
    TelegramConnectIn,
    TelegramStatusOut,
    TelegramVerifyIn,
    TelegramVerifyOut,
)
from verasig.domain.account import UserAccount
from verasig.domain.protocols import CodeInvalidError
from verasig.services.telegram_link.service import (
    TelegramLinkMissingError,
    connect,
    verify,
)
from verasig.services.telegram_link.service import (
    status as read_status,
)

router = APIRouter(prefix="/telegram")


@router.post("/connect", status_code=status.HTTP_202_ACCEPTED)
async def connect_telegram(
    request: Request,
    payload: TelegramConnectIn,
    user: UserAccount = Depends(get_current_user),
) -> Response:
    with request.app.state.session_factory() as session:
        await connect(
            session,
            user.id,
            payload.api_id,
            payload.api_hash,
            payload.phone,
            request.app.state.telegram_auth,
            request.app.state.secret_cipher,
        )
        session.commit()
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post("/verify")
async def verify_telegram(
    request: Request,
    payload: TelegramVerifyIn,
    user: UserAccount = Depends(get_current_user),
) -> TelegramVerifyOut:
    with request.app.state.session_factory() as session:
        try:
            await verify(
                session,
                user.id,
                payload.code,
                request.app.state.telegram_auth,
                request.app.state.secret_cipher,
            )
        except CodeInvalidError as error:
            raise ApiError(
                400, "TELEGRAM_CODE_INVALID", "Invalid Telegram code"
            ) from error
        except TelegramLinkMissingError as error:
            raise ApiError(
                409, "TELEGRAM_NOT_PENDING", "Telegram link is not pending"
            ) from error
        session.commit()
    return TelegramVerifyOut(connected=True)


@router.get("/status")
def telegram_status(
    request: Request, user: UserAccount = Depends(get_current_user)
) -> TelegramStatusOut:
    with request.app.state.session_factory() as session:
        return TelegramStatusOut(**read_status(session, user.id))
