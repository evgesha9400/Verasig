import hmac
import time
from collections.abc import Callable
from hashlib import sha256

import httpx

BYBIT_ACCOUNT_BASE_URL = "https://api.bybit.com"
BYBIT_QUERY_API_PATH = "/v5/user/query-api"
BYBIT_RECV_WINDOW = "5000"


class KeyVerificationError(Exception):
    pass


async def verify_api_keys(
    api_key: str,
    api_secret: str,
    transport: httpx.AsyncBaseTransport | None = None,
    timestamp_ms: Callable[[], int] | None = None,
) -> None:
    timestamp = str((timestamp_ms or _timestamp_ms)())
    headers = _signed_headers(api_key, api_secret, timestamp)
    try:
        async with httpx.AsyncClient(
            base_url=BYBIT_ACCOUNT_BASE_URL,
            transport=transport,
            timeout=10.0,
        ) as client:
            response = await client.get(BYBIT_QUERY_API_PATH, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise KeyVerificationError from error
    if response.json().get("retCode") != 0:
        raise KeyVerificationError


def _timestamp_ms() -> int:
    return int(time.time() * 1000)


def _signed_headers(api_key: str, api_secret: str, timestamp: str) -> dict[str, str]:
    return {
        "X-BAPI-API-KEY": api_key,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": BYBIT_RECV_WINDOW,
        "X-BAPI-SIGN": _signature(api_key, api_secret, timestamp),
    }


def _signature(api_key: str, api_secret: str, timestamp: str) -> str:
    payload = f"{timestamp}{api_key}{BYBIT_RECV_WINDOW}".encode()
    return hmac.new(api_secret.encode(), payload, sha256).hexdigest()
