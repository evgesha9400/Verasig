"""Pure market and exchange adapter seams."""

from datetime import datetime
from typing import Protocol, runtime_checkable

from verasig.domain.simulation import Kline


@runtime_checkable
class Exchange(Protocol):
    def is_listed(self, token: str) -> bool: ...
    def base_symbols(self) -> set[str]: ...


@runtime_checkable
class MarketData(Protocol):
    def klines(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1",
    ) -> list[Kline]: ...
