import hmac
from hashlib import sha256

import httpx
import pytest

from verasig.foundation.market_data.bybit_account import (
    KeyVerificationError,
    verify_api_keys,
)


@pytest.mark.asyncio
async def test_verify_api_keys_signs_bybit_query_api_request():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json={"retCode": 0})

    await verify_api_keys(
        "api-key",
        "api-secret",
        transport=httpx.MockTransport(handler),
        timestamp_ms=lambda: 1234567890,
    )

    request = captured["request"]
    expected = hmac.new(
        b"api-secret",
        b"1234567890api-key5000",
        sha256,
    ).hexdigest()
    assert str(request.url) == "https://api.bybit.com/v5/user/query-api"
    assert request.headers["X-BAPI-API-KEY"] == "api-key"
    assert request.headers["X-BAPI-TIMESTAMP"] == "1234567890"
    assert request.headers["X-BAPI-RECV-WINDOW"] == "5000"
    assert request.headers["X-BAPI-SIGN"] == expected


@pytest.mark.asyncio
async def test_verify_api_keys_rejects_nonzero_ret_code():
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"retCode": 10004, "retMsg": "invalid sign"})

    with pytest.raises(KeyVerificationError):
        await verify_api_keys(
            "api-key",
            "api-secret",
            transport=httpx.MockTransport(handler),
            timestamp_ms=lambda: 1234567890,
        )
