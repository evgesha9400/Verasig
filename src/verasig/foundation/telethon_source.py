"""Telethon Telegram adapter (data-contracts.md §9; ADR 0004).

`TelethonSource` is the real Telegram adapter behind the pure `TelegramSource`
seam in `domain.protocols`.
"""

import asyncio
import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from urllib.parse import urlparse

from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetFullChannelRequest

from verasig.domain.channel import TelegramChannel
from verasig.domain.message import DeliveryMode, RawTelegramMessage
from verasig.domain.protocols import TelegramSource
from verasig.domain.telegram import (
    TelegramDeletionEvent,
    TelegramDeliveryEvent,
    TelegramLiveEvent,
)


@dataclass
class _LiveEventState:
    channel_ids: set[int]
    queue: asyncio.Queue[TelegramLiveEvent] = field(default_factory=asyncio.Queue)
    seen_messages: set[tuple[int, int]] = field(default_factory=set)
    seen_deletions: set[tuple[int, int]] = field(default_factory=set)
    last_seen_message_ids: dict[int, int] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class ChannelReferenceResolutionError(ValueError):
    """A Telegram channel reference could not resolve to one channel."""


class ChannelReferenceKind(str, Enum):
    HANDLE = "handle"
    LINK = "link"
    ID = "id"
    TITLE = "title"


@dataclass(frozen=True)
class ChannelReference:
    kind: ChannelReferenceKind
    value: str | int


_TELEGRAM_HOSTS = frozenset({"t.me", "telegram.me", "telegram.dog"})
_TITLE_PREFIXES = ("title:", "dialog:", "name:")
_USERNAME_PATTERN = re.compile(r"^@?[A-Za-z0-9_]{5,32}$")


def _json_safe(payload: dict) -> dict:
    # verbatim-ish provenance: stringify datetimes/bytes Telethon embeds
    return json.loads(json.dumps(payload, default=str))


def parse_channel_reference(reference: str | int) -> ChannelReference:
    if isinstance(reference, int):
        return ChannelReference(ChannelReferenceKind.ID, reference)

    text = str(reference).strip()
    if not text:
        raise ChannelReferenceResolutionError("Telegram channel reference is empty")
    if _is_numeric_reference(text):
        return ChannelReference(ChannelReferenceKind.ID, int(text))
    if _is_title_reference(text):
        return ChannelReference(ChannelReferenceKind.TITLE, _strip_title_prefix(text))
    if _is_telegram_link(text):
        return ChannelReference(ChannelReferenceKind.LINK, text)
    if _is_username_reference(text):
        return ChannelReference(ChannelReferenceKind.HANDLE, _normalize_handle(text))
    return ChannelReference(ChannelReferenceKind.TITLE, text)


def _is_numeric_reference(text: str) -> bool:
    return text.removeprefix("-").isdigit()


def _is_title_reference(text: str) -> bool:
    return any(text.casefold().startswith(prefix) for prefix in _TITLE_PREFIXES)


def _strip_title_prefix(text: str) -> str:
    for prefix in _TITLE_PREFIXES:
        if text.casefold().startswith(prefix):
            title = text[len(prefix) :].strip()
            if not title:
                raise ChannelReferenceResolutionError("Telegram channel title is empty")
            return title
    return text


def _is_telegram_link(text: str) -> bool:
    parsed = urlparse(text if "://" in text else f"https://{text}")
    return parsed.netloc.casefold() in _TELEGRAM_HOSTS and bool(parsed.path.strip("/"))


def _is_username_reference(text: str) -> bool:
    return bool(_USERNAME_PATTERN.fullmatch(text))


def _normalize_handle(text: str) -> str:
    return text if text.startswith("@") else f"@{text}"


def _normalize_title(text: str) -> str:
    return " ".join(text.split()).casefold()


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

    async def resolve_channel(self, reference: str | int) -> TelegramChannel:
        channel_reference = parse_channel_reference(reference)
        entity = await self._resolve_entity(channel_reference)
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
            raise ChannelReferenceResolutionError(
                "Cannot resolve Telegram channel reference "
                f"{reference.value!r}. Use @handle, t.me link, numeric id, "
                "or title:<exact joined dialog title>."
            ) from error

    async def _resolve_title_entity(self, title: str):
        wanted = _normalize_title(title)
        matches = []
        async for dialog in self._client.iter_dialogs():
            if _normalize_title(_dialog_title(dialog)) == wanted:
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

    def _to_raw_message(
        self, channel_id: int, message, captured_at: datetime | None = None
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

    async def live_message_ids(self, channel_id: int) -> set[int]:
        # full live id set for snapshot-diff
        return {message.id async for message in self._client.iter_messages(channel_id)}

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

    async def _enqueue_deleted_messages(self, state: _LiveEventState, event) -> None:
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
