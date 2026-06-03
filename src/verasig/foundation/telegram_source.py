"""Telegram ingestion seam (data-contracts.md §9; ADR 0004).

Protocol-only this slice: `backfill_batches` is implemented by `TelethonSource`
in Slice 2, `live_events` in Slice 11. Defined here so every external
dependency sits behind a Protocol that tests can fake offline.
"""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from verasig.domain.channel import TelegramChannel
from verasig.domain.message import DeliveryMode, RawTelegramMessage


class TelegramDeliveryEvent(BaseModel):
    """A live message plus its latency provenance (which path delivered it)."""

    message: RawTelegramMessage
    mode: DeliveryMode
    captured_at: datetime
    source_pts: int | None = None
    gap_closed: bool


@runtime_checkable
class TelegramSource(Protocol):
    # resolve: @handle | t.me link | numeric id -> channel identity + metadata.
    async def resolve_channel(self, reference: str | int) -> TelegramChannel: ...

    # backfill: chunked + resumable — one committable batch at a time.
    def backfill_batches(
        self, channel_id: int, after_message_id: int | None, batch_size: int
    ) -> AsyncIterator[list[RawTelegramMessage]]: ...

    # live: one global socket, many channels; hybrid push + short-poll inside.
    def live_events(
        self, channel_ids: list[int]
    ) -> AsyncIterator[TelegramDeliveryEvent]: ...
