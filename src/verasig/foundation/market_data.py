"""Market-data seam for historical kline replay (data-contracts.md §9)."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol, runtime_checkable

import httpx

from verasig.domain.simulation import Kline

BYBIT_PUBLIC_BASE_URL = "https://api.bybit.com"
BYBIT_KLINE_PATH = "/v5/market/kline"
BYBIT_DEFAULT_CATEGORY = "linear"
BYBIT_KLINE_LIMIT = 1000


@runtime_checkable
class MarketData(Protocol):
    def klines(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1",
    ) -> list[Kline]: ...


class BybitKlineClient:
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
        response = self._http_client.get(
            BYBIT_KLINE_PATH,
            params=_kline_params(self._category, symbol, start, end, interval),
        )
        response.raise_for_status()
        return _parse_klines(response.json(), symbol)


def _kline_params(
    category: str,
    symbol: str,
    start: datetime,
    end: datetime,
    interval: str,
) -> dict[str, str | int]:
    return {
        "category": category,
        "symbol": symbol.upper(),
        "interval": interval,
        "start": _to_millis(start),
        "end": _to_millis(end),
        "limit": BYBIT_KLINE_LIMIT,
    }


def _to_millis(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _parse_klines(payload: dict, requested_symbol: str) -> list[Kline]:
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
