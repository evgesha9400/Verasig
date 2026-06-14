from fastapi import APIRouter, Depends, Request, Response, status

from verasig.domain.account import UserAccount
from verasig.domain.telegram_ports import (
    CodeInvalidError,
    TwoFactorPasswordInvalidError,
    TwoFactorUnsupportedError,
)
from verasig.features.telegram_links.schemas import (
    TelegramConnectIn,
    TelegramStatusOut,
    TelegramVerifyIn,
    TelegramVerifyOut,
)
from verasig.features.telegram_links.workflow import (
    TelegramLinkMissingError,
    connect,
    verify,
)
from verasig.features.telegram_links.workflow import (
    status as read_status,
)
from verasig.foundation.http.auth_dependencies import get_current_user
from verasig.foundation.http.errors import ApiError

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
                payload.password,
            )
        except CodeInvalidError as error:
            raise ApiError(
                400, "TELEGRAM_CODE_INVALID", "Invalid Telegram code"
            ) from error
        except TwoFactorPasswordInvalidError as error:
            raise ApiError(
                400, "TELEGRAM_PASSWORD_INVALID", "Invalid Telegram password"
            ) from error
        except TwoFactorUnsupportedError as error:
            raise ApiError(
                400, "TELEGRAM_TWO_FACTOR_REQUIRED", "Two-factor password required"
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
