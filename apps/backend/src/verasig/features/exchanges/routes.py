from fastapi import APIRouter, Depends, Request

from verasig.domain.account import UserAccount
from verasig.features.exchanges.schemas import ExchangeConnectIn
from verasig.features.exchanges.workflow import (
    ExchangePlanLimitError,
    ExchangeUnavailableError,
    connect_exchange,
    disconnect_exchange,
    present_exchanges,
)
from verasig.foundation.http.auth_dependencies import get_current_user
from verasig.foundation.http.errors import ApiError
from verasig.foundation.market_data.bybit_account import KeyVerificationError

router = APIRouter(prefix="/exchanges")


@router.get("")
def list_exchanges(
    request: Request, user: UserAccount = Depends(get_current_user)
) -> dict:
    with request.app.state.session_factory() as session:
        return {"exchanges": present_exchanges(session, user.id)}


@router.post("/{exchange_id}/connect")
async def connect(
    request: Request,
    exchange_id: str,
    payload: ExchangeConnectIn,
    user: UserAccount = Depends(get_current_user),
) -> dict:
    try:
        with request.app.state.session_factory() as session:
            exchange = await connect_exchange(
                session,
                user,
                exchange_id,
                payload.api_key,
                payload.api_secret,
                request.app.state.secret_cipher,
                request.app.state.exchange_verifier,
            )
            session.commit()
            return exchange
    except ExchangePlanLimitError as error:
        raise ApiError(403, "PLAN_LIMIT_EXCHANGES", "Exchange limit reached") from error
    except ExchangeUnavailableError as error:
        raise ApiError(404, "EXCHANGE_NOT_FOUND", "Exchange not found") from error
    except KeyVerificationError as error:
        raise ApiError(
            400, "EXCHANGE_KEYS_INVALID", "Exchange keys are invalid"
        ) from error


@router.post("/{exchange_id}/disconnect")
def disconnect(
    request: Request,
    exchange_id: str,
    user: UserAccount = Depends(get_current_user),
) -> dict:
    try:
        with request.app.state.session_factory() as session:
            exchange = disconnect_exchange(session, user.id, exchange_id)
            session.commit()
            return exchange
    except ExchangeUnavailableError as error:
        raise ApiError(404, "EXCHANGE_NOT_FOUND", "Exchange not found") from error
