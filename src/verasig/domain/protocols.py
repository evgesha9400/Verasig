"""Pure Protocol seams for adapters and injectable service policies."""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Protocol, runtime_checkable

from verasig.domain.channel import TelegramChannel
from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel
from verasig.domain.lifecycle import FoldedSignal
from verasig.domain.message import RawTelegramMessage
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import TradeIntent
from verasig.domain.simulation import Kline, SimOutcome
from verasig.domain.telegram import TelegramLiveEvent


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


@runtime_checkable
class LlmExtractor(Protocol):
    def extract(self, candidate_text: str) -> TradeIntent | None: ...


@runtime_checkable
class RuleDistiller(Protocol):
    def distill_filter(self, labels: list[GoldenLabel]) -> FilterRule: ...
    def distill_parsers(self, labels: list[GoldenLabel]) -> list[ParserRule]: ...


@runtime_checkable
class ExecutionPolicy(Protocol):
    def simulate(self, folded: FoldedSignal, klines: list[Kline]) -> SimOutcome: ...


@runtime_checkable
class TelegramSource(Protocol):
    async def resolve_channel(self, reference: str | int) -> TelegramChannel: ...

    def backfill_batches(
        self, channel_id: int, after_message_id: int | None, batch_size: int
    ) -> AsyncIterator[list[RawTelegramMessage]]: ...

    async def live_message_ids(self, channel_id: int) -> set[int]: ...

    def live_events(
        self, channel_ids: list[int]
    ) -> AsyncIterator[TelegramLiveEvent]: ...
