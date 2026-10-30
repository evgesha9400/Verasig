from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from verasig.domain.account import UserAccount
from verasig.features.accounts.plans import PLAN_LIMITS
from verasig.features.exchanges import repository as exchange_repository
from verasig.features.exchanges.catalog import EXCHANGE_CATALOG, catalog_item
from verasig.foundation.security.secrets import SecretCipher


class ExchangeUnavailableError(Exception):
    pass


class ExchangePlanLimitError(Exception):
    pass


type ExchangeVerifier = Callable[[str, str], Awaitable[None]]


def present_exchanges(session: Session, user_id: UUID) -> list[dict]:
    connections = {
        row.exchange_id: row
        for row in exchange_repository.read_connections(session, user_id)
    }
    return [
        _present_exchange(exchange, connections.get(exchange["id"]))
        for exchange in EXCHANGE_CATALOG
    ]


async def connect_exchange(
    session: Session,
    user: UserAccount,
    exchange_id: str,
    api_key: str,
    api_secret: str,
    cipher: SecretCipher,
    verifier: ExchangeVerifier,
) -> dict:
    exchange = _available_exchange(exchange_id)
    _require_exchange_capacity(session, user, exchange_id)
    await verifier(api_key, api_secret)
    connection = exchange_repository.upsert_connection(
        session,
        user.id,
        exchange_id,
        _mask_api_key(api_key),
        cipher.encrypt(api_key, _exchange_aad(user.id, exchange_id)),
        cipher.encrypt(api_secret, _exchange_aad(user.id, exchange_id)),
        True,
        datetime.now(tz=UTC),
    )
    return _present_exchange(exchange, connection)


def disconnect_exchange(session: Session, user_id: UUID, exchange_id: str) -> dict:
    exchange = _available_exchange(exchange_id)
    connection = exchange_repository.set_connected(session, user_id, exchange_id, False)
    return _present_exchange(exchange, connection)


def _present_exchange(exchange: dict, connection) -> dict:
    connected = bool(connection and connection.connected)
    return {
        **exchange,
        "connected": connected,
        "account": connection.api_key_masked if connected else None,
    }


def _available_exchange(exchange_id: str) -> dict:
    exchange = catalog_item(exchange_id)
    if exchange is None or exchange["status"] != "available":
        raise ExchangeUnavailableError
    return exchange


def _require_exchange_capacity(
    session: Session, user: UserAccount, exchange_id: str
) -> None:
    limit = PLAN_LIMITS[user.plan].exchanges
    if limit is None:
        return
    if _connected_exchange_count(session, user.id, exchange_id) < limit:
        return
    raise ExchangePlanLimitError


def _connected_exchange_count(session: Session, user_id: UUID, exchange_id: str) -> int:
    return sum(
        1
        for row in exchange_repository.read_connections(session, user_id)
        if row.connected and row.exchange_id != exchange_id
    )


def _mask_api_key(api_key: str) -> str:
    return f"{api_key[:4]}…{api_key[-2:]} · trade-only"


def _exchange_aad(user_id: UUID, exchange_id: str) -> str:
    return f"{user_id}:exchange:{exchange_id}"
