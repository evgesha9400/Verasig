"""Telegram channel contract (data-contracts.md §2).

The message table is append-only; the channel row is mutable metadata
(subscriber_count refresh, advancing `captured_through_message_id` cursor).
The ORM row and Alembic table mirror this contract.
"""

from datetime import datetime

from pydantic import BaseModel


class TelegramChannel(BaseModel):
    channel_id: int
    handle: str | None = None
    title: str
    is_private: bool
    subscriber_count: int | None = None
    first_seen_at: datetime
    captured_through_message_id: int | None = None
