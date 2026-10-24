"""Bybit market-data adapter for historical kline replay.

Bybit returns at most `BYBIT_KLINE_LIMIT` bars per request, newest first, so a
longer window is read page by page backwards from `end` until it reaches
`start`. A non-zero `retCode` is an API error, never an empty kline window.
"""

from datetime import datetime, timezone
from decimal import Decimal

import httpx

from verasig.domain.market_ports import MarketData
from verasig.domain.simulation import Kline

BYBIT_PUBLIC_BASE_URL = "https://api.bybit.com"
BYBIT_KLINE_PATH = "/v5/market/kline"
BYBIT_DEFAULT_CATEGORY = "linear"
BYBIT_KLINE_LIMIT = 1000


class BybitApiError(RuntimeError):
    """Bybit answered HTTP 200 with a non-zero `retCode`."""


class BybitKlineClient(MarketData):
    """Bybit public kline adapter; tests inject an httpx mock transport."""

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        category: str = BYBIT_DEFAULT_CATEGORY,
    ) -> None:
        self._http_client = http_client or httpx.Client(
            base_url=BYBIT_PUBLIC_BASE_URL,
            timeout=10.0,
        )
        self._category = category

    def klines(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1",
    ) -> list[Kline]:
        start_ms = _to_millis(start)
        end_ms = _to_millis(end)
        by_open_time: dict[datetime, Kline] = {}
        while True:
            page = self._page(symbol, interval, start_ms, end_ms)
            by_open_time.update((kline.open_time, kline) for kline in page)
            if len(page) < BYBIT_KLINE_LIMIT:
                break
            earliest_ms = _to_millis(page[0].open_time)
            if earliest_ms <= start_ms or earliest_ms - 1 >= end_ms:
                break  # the window is covered, or the page did not move back
            end_ms = earliest_ms - 1
        return sorted(by_open_time.values(), key=lambda item: item.open_time)

    def _page(
        self, symbol: str, interval: str, start_ms: int, end_ms: int
    ) -> list[Kline]:
        response = self._http_client.get(
            BYBIT_KLINE_PATH,
            params=_kline_params(self._category, symbol, start_ms, end_ms, interval),
        )
        response.raise_for_status()
        return _parse_klines(response.json(), symbol)


def _kline_params(
    category: str,
    symbol: str,
    start_ms: int,
    end_ms: int,
    interval: str,
) -> dict[str, str | int]:
    return {
        "category": category,
        "symbol": symbol.upper(),
        "interval": interval,
        "start": start_ms,
        "end": end_ms,
        "limit": BYBIT_KLINE_LIMIT,
    }


def _to_millis(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _parse_klines(payload: dict, requested_symbol: str) -> list[Kline]:
    ret_code = payload.get("retCode", 0)
    if ret_code != 0:
        raise BybitApiError(f"Bybit error {ret_code}: {payload.get('retMsg')}")
    result = payload.get("result", {})
    symbol = result.get("symbol") or requested_symbol.upper()
    klines = [_parse_kline(symbol, row) for row in result.get("list", [])]
    return sorted(klines, key=lambda item: item.open_time)


def _parse_kline(symbol: str, row: list[str]) -> Kline:
    return Kline(
        symbol=symbol,
        open_time=_from_millis(row[0]),
        open=Decimal(row[1]),
        high=Decimal(row[2]),
        low=Decimal(row[3]),
        close=Decimal(row[4]),
        volume=Decimal(row[5]),
    )


def _from_millis(value: str) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
