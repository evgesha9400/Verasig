"""Raw Telegram capture contracts (data-contracts.md §2, §1 DeliveryMode).

`RawTelegramMessage` is the immutable, append-only 100%-capture record.
`DeliveryMode` tags how a live message reached us (latency provenance; ADR 0004).
The ORM row and Alembic table mirror the capture contract.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class DeliveryMode(StrEnum):
    PUSH = "PUSH"
    POLL = "POLL"
    CATCH_UP = "CATCH_UP"


class RawTelegramMessage(BaseModel):
    channel_id: int
    message_id: int
    text: str | None = None
    sender_id: int | None = None
    posted_at: datetime
    captured_at: datetime
    reply_to_message_id: int | None = None
    edit_date: datetime | None = None
    has_media: bool
    views: int | None = None
    forwards: int | None = None
    raw_payload: dict
