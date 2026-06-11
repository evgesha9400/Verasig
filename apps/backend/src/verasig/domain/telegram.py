"""Pure Telegram live-event contracts (data-contracts.md §9; ADR 0004)."""

from datetime import datetime

from pydantic import BaseModel

from verasig.domain.message import DeliveryMode, RawTelegramMessage


class TelegramDeliveryEvent(BaseModel):
    """A live message plus its latency provenance."""

    message: RawTelegramMessage
    mode: DeliveryMode
    captured_at: datetime
    source_pts: int | None = None
    gap_closed: bool


class TelegramDeletionEvent(BaseModel):
    """A live deletion notice for one message id."""

    channel_id: int
    message_id: int
    detected_at: datetime
    source_pts: int | None = None


TelegramLiveEvent = TelegramDeliveryEvent | TelegramDeletionEvent
