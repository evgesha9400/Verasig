"""Market-data seam for historical kline replay (data-contracts.md §9)."""

from datetime import datetime
from typing import Protocol, runtime_checkable

from verasig.domain.simulation import Kline


@runtime_checkable
class MarketData(Protocol):
    def klines(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1",
    ) -> list[Kline]: ...
