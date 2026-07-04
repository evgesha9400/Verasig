"""Telethon Telegram adapter (data-contracts.md §9; ADR 0004).

`TelethonSource` is the real Telegram adapter behind the pure `TelegramSource` seam.
"""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetFullChannelRequest

from verasig.domain.channel import TelegramChannel
from verasig.domain.channel_reference import (
    ChannelReference,
    ChannelReferenceKind,
    ChannelReferenceResolutionError,
    normalize_channel_title,
    parse_channel_reference,
)
from verasig.domain.message import DeliveryMode, RawTelegramMessage
from verasig.domain.telegram import (
    TelegramDeletionEvent,
    TelegramDeliveryEvent,
    TelegramLiveEvent,
)
from verasig.domain.telegram_ports import TelegramSource


@dataclass
class _LiveEventState:
    channel_ids: set[int]
    queue: asyncio.Queue[TelegramLiveEvent] = field(default_factory=asyncio.Queue)
    seen_messages: set[tuple[int, int]] = field(default_factory=set)
    seen_deletions: set[tuple[int, int]] = field(default_factory=set)
    last_seen_message_ids: dict[int, int] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def _json_safe(payload: dict) -> dict:
    # verbatim-ish provenance: stringify datetimes/bytes Telethon embeds
    return json.loads(json.dumps(payload, default=str))


def _dialog_title(dialog) -> str:
    entity = getattr(dialog, "entity", None)
    return getattr(entity, "title", None) or getattr(dialog, "name", None) or ""


def _describe_entity(entity) -> str:
    parts = [f"id={getattr(entity, 'id', '?')}"]
    username = getattr(entity, "username", None)
    if username:
        parts.append(f"@{username}")
    title = getattr(entity, "title", None)
    if title:
        parts.append(str(title))
    return " ".join(parts)


class TelethonSource(TelegramSource):
    """Telegram adapter over one Telethon client."""

    def __init__(
        self, client: TelegramClient, poll_interval_seconds: float = 4.0
    ) -> None:
        self._client = client
        self._poll_interval_seconds = poll_interval_seconds
        self._entities_by_channel_id: dict[int, Any] = {}

    async def __aenter__(self) -> "TelethonSource":
        await self._client.connect()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._client.disconnect()

    async def resolve_channel(self, reference: str | int) -> TelegramChannel:
        channel_reference = parse_channel_reference(reference)
        entity = await self._resolve_entity(channel_reference)
        self._remember_entity(entity)
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

    async def _resolve_entity(self, reference: ChannelReference):
        if reference.kind is ChannelReferenceKind.TITLE:
            return await self._resolve_title_entity(str(reference.value))
        return await self._resolve_direct_entity(reference)

    async def _resolve_direct_entity(self, reference: ChannelReference):
        try:
            return await self._client.get_entity(reference.value)
        except (TypeError, ValueError) as error:
            if reference.kind is ChannelReferenceKind.ID:
                entity = await self._resolve_dialog_id_entity(int(reference.value))
                if entity is not None:
                    return entity
            raise ChannelReferenceResolutionError(
                "Cannot resolve Telegram channel reference "
                f"{reference.value!r}. Use @handle, t.me link, numeric id, "
                "or title:<exact joined dialog title>."
            ) from error

    async def _resolve_dialog_id_entity(self, channel_id: int) -> Any | None:
        wanted = _normalize_chat_id(channel_id)
        async for dialog in self._client.iter_dialogs():
            entity = getattr(dialog, "entity", None)
            if _entity_channel_id(entity) == wanted:
                return entity
        return None

    async def _resolve_title_entity(self, title: str):
        wanted = normalize_channel_title(title)
        matches = []
        async for dialog in self._client.iter_dialogs():
            if normalize_channel_title(_dialog_title(dialog)) == wanted:
                matches.append(dialog.entity)
        if not matches:
            raise ChannelReferenceResolutionError(
                f"No joined dialog has title {title!r}. Use @handle, t.me link, "
                "numeric id, or title:<exact joined dialog title>."
            )
        if len(matches) > 1:
            options = "; ".join(_describe_entity(entity) for entity in matches)
            raise ChannelReferenceResolutionError(
                f"Found multiple joined dialogs with title {title!r}: {options}. "
                "Use @handle or numeric id."
            )
        return matches[0]

    async def fetch_older_batches(
        self,
        channel_id: int,
        before_message_id: int | None,
        batch_size: int,
        since: datetime | None = None,
    ) -> AsyncIterator[list[RawTelegramMessage]]:
        # reverse=False streams newest->oldest; offset_id excludes ids >= it, so we
        # page strictly older than what we already hold. The depth cutoff is a
        # manual break (offset_date would bound the wrong end here): stop BEFORE
        # keeping the first message past `since`, so no out-of-window message leaks.
        batch: list[RawTelegramMessage] = []
        entity = self._read_entity(channel_id)
        messages = self._client.iter_messages(
            entity, reverse=False, offset_id=before_message_id or 0
        )
        async for message in messages:  # Telethon auto-sleeps short flood-waits
            if since is not None and message.date < since:
                break
            batch.append(self._to_raw_message(channel_id, message))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    async def fetch_newer_batches(
        self,
        channel_id: int,
        after_message_id: int | None,
        batch_size: int,
    ) -> AsyncIterator[list[RawTelegramMessage]]:
        # reverse=False streams newest->oldest; min_id excludes ids <= it, so we
        # capture only the messages posted since the last capture (REFRESH).
        batch: list[RawTelegramMessage] = []
        entity = self._read_entity(channel_id)
        messages = self._client.iter_messages(
            entity, reverse=False, min_id=after_message_id or 0
        )
        async for message in messages:
            batch.append(self._to_raw_message(channel_id, message))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    @staticmethod
    def _to_raw_message(
        channel_id: int, message, captured_at: datetime | None = None
    ) -> RawTelegramMessage:
        return RawTelegramMessage(
            channel_id=channel_id,
            message_id=message.id,
            text=message.message,
            sender_id=message.sender_id,
            posted_at=message.date,
            captured_at=captured_at or datetime.now(tz=timezone.utc),
            reply_to_message_id=message.reply_to_msg_id,
            edit_date=message.edit_date,
            has_media=message.media is not None,
            views=getattr(message, "views", None),
            forwards=getattr(message, "forwards", None),
            raw_payload=_json_safe(message.to_dict()),
        )

    async def live_message_ids(
        self, channel_id: int, on_progress: Callable[[int], None] | None = None
    ) -> set[int]:
        # full live id set for snapshot-diff; report the running count so a long
        # re-fetch never goes silent to progress subscribers
        entity = await self._read_live_entity(channel_id)
        live_ids: set[int] = set()
        async for message in self._client.iter_messages(entity):
            live_ids.add(message.id)
            if on_progress is not None:
                on_progress(len(live_ids))
        return live_ids

    def _remember_entity(self, entity: Any) -> None:
        channel_id = _entity_channel_id(entity)
        if channel_id is not None:
            self._entities_by_channel_id[channel_id] = entity

    def _read_entity(self, channel_id: int) -> Any:
        normalized = _normalize_chat_id(channel_id)
        return self._entities_by_channel_id.get(normalized, channel_id)

    async def _read_live_entity(self, channel_id: int) -> Any:
        normalized = _normalize_chat_id(channel_id)
        if normalized in self._entities_by_channel_id:
            return self._entities_by_channel_id[normalized]
        entity = await self._resolve_channel_id_for_read(channel_id)
        self._remember_entity(entity)
        return entity

    async def _resolve_channel_id_for_read(self, channel_id: int) -> Any:
        try:
            entity = await self._client.get_entity(channel_id)
        except (TypeError, ValueError):
            entity = await self._resolve_dialog_id_entity(channel_id)
            return entity if entity is not None else channel_id
        return entity

    async def live_events(
        self, channel_ids: list[int]
    ) -> AsyncIterator[TelegramLiveEvent]:
        state = _LiveEventState(channel_ids=set(channel_ids))

        async def push_handler(event) -> None:
            await self._enqueue_push_delivery(state, event)

        async def delete_handler(event) -> None:
            await self._enqueue_deleted_messages(state, event)

        push_event = events.NewMessage(chats=channel_ids)
        delete_event = events.MessageDeleted(chats=channel_ids)
        self._client.add_event_handler(push_handler, push_event)
        self._client.add_event_handler(delete_handler, delete_event)
        poll_tasks = [
            asyncio.create_task(self._poll_channel(state, channel_id))
            for channel_id in channel_ids
        ]
        try:
            while True:
                yield await state.queue.get()
        finally:
            for task in poll_tasks:
                task.cancel()
            await asyncio.gather(*poll_tasks, return_exceptions=True)
            self._client.remove_event_handler(push_handler, push_event)
            self._client.remove_event_handler(delete_handler, delete_event)

    async def _poll_channel(self, state: _LiveEventState, channel_id: int) -> None:
        while True:
            await self._poll_channel_once(state, channel_id)
            await asyncio.sleep(self._poll_interval_seconds)

    async def _poll_channel_once(self, state: _LiveEventState, channel_id: int) -> None:
        after_message_id = state.last_seen_message_ids.get(channel_id, 0)
        if after_message_id == 0:
            await self._poll_latest_message_once(state, channel_id)
            return
        messages = self._client.iter_messages(
            channel_id, reverse=True, min_id=after_message_id
        )
        async for message in messages:
            await self._enqueue_delivery(
                state, channel_id, message, DeliveryMode.POLL, gap_closed=True
            )

    async def _poll_latest_message_once(
        self, state: _LiveEventState, channel_id: int
    ) -> None:
        messages = self._client.iter_messages(channel_id, limit=1)
        async for message in messages:
            await self._enqueue_delivery(
                state, channel_id, message, DeliveryMode.CATCH_UP, gap_closed=True
            )

    async def _enqueue_push_delivery(self, state: _LiveEventState, event) -> None:
        message = event.message
        channel_id = _message_channel_id(event, message)
        if channel_id not in state.channel_ids:
            return
        await self._enqueue_delivery(
            state, channel_id, message, DeliveryMode.PUSH, gap_closed=False
        )

    async def _enqueue_delivery(
        self,
        state: _LiveEventState,
        channel_id: int,
        message,
        mode: DeliveryMode,
        *,
        gap_closed: bool,
    ) -> None:
        captured_at = datetime.now(tz=timezone.utc)
        key = (channel_id, message.id)
        async with state.lock:
            if key in state.seen_messages:
                return
            state.seen_messages.add(key)
            _advance_last_seen(state, channel_id, message.id)
        await state.queue.put(
            TelegramDeliveryEvent(
                message=self._to_raw_message(channel_id, message, captured_at),
                mode=mode,
                captured_at=captured_at,
                source_pts=getattr(message, "pts", None),
                gap_closed=gap_closed,
            )
        )

    @staticmethod
    async def _enqueue_deleted_messages(state: _LiveEventState, event) -> None:
        channel_id = _deletion_channel_id(event)
        if channel_id not in state.channel_ids:
            return
        detected_at = datetime.now(tz=timezone.utc)
        for message_id in event.deleted_ids:
            await _enqueue_deletion(state, channel_id, message_id, detected_at)


def _advance_last_seen(
    state: _LiveEventState, channel_id: int, message_id: int
) -> None:
    current = state.last_seen_message_ids.get(channel_id, 0)
    if message_id > current:
        state.last_seen_message_ids[channel_id] = message_id


def _normalize_chat_id(value) -> int | None:
    if value is None:
        return None
    raw = abs(int(value))
    text = str(raw)
    if text.startswith("100") and len(text) > 3:
        return int(text[3:])
    return raw


def _entity_channel_id(entity: Any) -> int | None:
    return _normalize_chat_id(getattr(entity, "id", None))


def _message_channel_id(event, message) -> int | None:
    peer_id = getattr(message, "peer_id", None)
    channel_id = getattr(peer_id, "channel_id", None)
    if channel_id is not None:
        return int(channel_id)
    return _normalize_chat_id(getattr(event, "chat_id", None))


def _deletion_channel_id(event) -> int | None:
    peer = getattr(event, "chat_peer", None)
    channel_id = getattr(peer, "channel_id", None)
    if channel_id is not None:
        return int(channel_id)
    return _normalize_chat_id(getattr(event, "chat_id", None))


async def _enqueue_deletion(
    state: _LiveEventState, channel_id: int, message_id: int, detected_at: datetime
) -> None:
    key = (channel_id, message_id)
    async with state.lock:
        if key in state.seen_deletions:
            return
        state.seen_deletions.add(key)
    await state.queue.put(
        TelegramDeletionEvent(
            channel_id=channel_id,
            message_id=message_id,
            detected_at=detected_at,
        )
    )
