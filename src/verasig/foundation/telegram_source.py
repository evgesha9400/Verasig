"""Telegram ingestion seam (data-contracts.md §9; ADR 0004).

`TelegramSource` is the Protocol every consumer codes against; tests inject a
fake. `TelethonSource` is the real adapter — its `resolve_channel`/
`backfill_batches` are exercised by manual acceptance against a real account
(never in tests); `live_events` is exercised by manual Slice 10 acceptance.
"""

import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from pydantic import BaseModel
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest

from verasig.domain.channel import TelegramChannel
from verasig.domain.message import DeliveryMode, RawTelegramMessage


class TelegramDeliveryEvent(BaseModel):
    """A live message plus its latency provenance (which path delivered it)."""

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


@runtime_checkable
class TelegramSource(Protocol):
    # resolve: @handle | t.me link | numeric id -> channel identity + metadata.
    async def resolve_channel(self, reference: str | int) -> TelegramChannel: ...

    # backfill: chunked + resumable — one committable batch at a time.
    def backfill_batches(
        self, channel_id: int, after_message_id: int | None, batch_size: int
    ) -> AsyncIterator[list[RawTelegramMessage]]: ...

    # deletion rescan: the channel's CURRENT live message-id set (Slice 7, ADR 0008).
    async def live_message_ids(self, channel_id: int) -> set[int]: ...

    # live: one global socket, many channels; hybrid push + short-poll inside.
    def live_events(
        self, channel_ids: list[int]
    ) -> AsyncIterator[TelegramLiveEvent]: ...


def _json_safe(payload: dict) -> dict:
    # verbatim-ish provenance: stringify datetimes/bytes Telethon embeds
    return json.loads(json.dumps(payload, default=str))


class TelethonSource:
    """Real Telegram adapter over one Telethon client (manual acceptance)."""

    def __init__(self, client: TelegramClient) -> None:
        self._client = client

    async def resolve_channel(self, reference: str | int) -> TelegramChannel:
        entity = await self._client.get_entity(reference)
        full = await self._client(GetFullChannelRequest(entity))
        handle = getattr(entity, "username", None)
        return TelegramChannel(
            channel_id=entity.id,
            handle=handle,
            title=getattr(entity, "title", "") or "",
            is_private=handle is None,
            subscriber_count=full.full_chat.participants_count,
            first_seen_at=datetime.now(tz=timezone.utc),
        )

    async def backfill_batches(
        self, channel_id: int, after_message_id: int | None, batch_size: int
    ) -> AsyncIterator[list[RawTelegramMessage]]:
        batch: list[RawTelegramMessage] = []
        messages = self._client.iter_messages(
            channel_id, reverse=True, min_id=after_message_id or 0
        )
        async for message in messages:  # Telethon auto-sleeps short flood-waits
            batch.append(self._to_raw_message(channel_id, message))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def _to_raw_message(self, channel_id: int, message) -> RawTelegramMessage:
        return RawTelegramMessage(
            channel_id=channel_id,
            message_id=message.id,
            text=message.message,
            sender_id=message.sender_id,
            posted_at=message.date,
            captured_at=datetime.now(tz=timezone.utc),
            reply_to_message_id=message.reply_to_msg_id,
            edit_date=message.edit_date,
            has_media=message.media is not None,
            views=getattr(message, "views", None),
            forwards=getattr(message, "forwards", None),
            raw_payload=_json_safe(message.to_dict()),
        )

    async def live_message_ids(self, channel_id: int) -> set[int]:
        # full live id set for snapshot-diff (manual acceptance, never in tests)
        return {message.id async for message in self._client.iter_messages(channel_id)}

    async def live_events(
        self, channel_ids: list[int]
    ) -> AsyncIterator[TelegramLiveEvent]:
        raise NotImplementedError("live listener arrives in Slice 10")
        yield  # pragma: no cover - marks this as an async generator
