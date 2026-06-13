import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

from verasig.foundation.market_data.bybit_market_data import BybitKlineClient

_FIXTURE = Path("tests/fixtures/klines/bybit_linear_btcusdt_response.json")


def test_bybit_kline_client_maps_response_to_chronological_klines():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=json.loads(_FIXTURE.read_text()))

    http_client = httpx.Client(
        base_url="https://api.bybit.test",
        transport=httpx.MockTransport(handler),
    )
    client = BybitKlineClient(http_client=http_client)
    start = datetime(2022, 12, 9, 16, 0, tzinfo=timezone.utc)
    end = datetime(2022, 12, 9, 18, 0, tzinfo=timezone.utc)

    klines = client.klines("BTCUSDT", start, end, interval="60")

    assert requests[0].url.path == "/v5/market/kline"
    assert requests[0].url.params["category"] == "linear"
    assert requests[0].url.params["symbol"] == "BTCUSDT"
    assert requests[0].url.params["interval"] == "60"
    assert requests[0].url.params["start"] == "1670601600000"
    assert requests[0].url.params["end"] == "1670608800000"
    assert [item.open_time for item in klines] == [
        datetime(2022, 12, 9, 16, 0, tzinfo=timezone.utc),
        datetime(2022, 12, 9, 17, 0, tzinfo=timezone.utc),
        datetime(2022, 12, 9, 18, 0, tzinfo=timezone.utc),
    ]
    assert klines[0].symbol == "BTCUSDT"
    assert klines[0].open == Decimal("17086.5")
    assert klines[0].high == Decimal("17088")
    assert klines[0].low == Decimal("16978")
    assert klines[0].close == Decimal("17071.5")
    assert klines[0].volume == Decimal("6356")
