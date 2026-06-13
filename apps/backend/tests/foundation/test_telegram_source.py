import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import pytest

from verasig.domain.channel import TelegramChannel
from verasig.domain.message import DeliveryMode, RawTelegramMessage
from verasig.domain.telegram import (
    TelegramDeletionEvent,
    TelegramDeliveryEvent,
)
from verasig.domain.telegram_ports import TelegramSource
from verasig.foundation.telegram.telethon_source import (
    ChannelReferenceResolutionError,
    TelethonSource,
)


def _instant() -> datetime:
    return datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)


def _message() -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=1,
        message_id=2,
        posted_at=_instant(),
        captured_at=_instant(),
        has_media=False,
        raw_payload={},
    )


def test_delivery_event_wraps_message_with_mode_and_defaults_source_pts():
    event = TelegramDeliveryEvent(
        message=_message(),
        mode=DeliveryMode.PUSH,
        captured_at=_instant(),
        gap_closed=False,
    )
    assert event.message.message_id == 2
    assert event.mode is DeliveryMode.PUSH
    assert event.source_pts is None


def test_conforming_source_satisfies_protocol():
    class FakeSource:
        @staticmethod
        async def resolve_channel(_reference) -> TelegramChannel:
            return TelegramChannel(
                channel_id=1,
                title="t",
                is_private=False,
                first_seen_at=_instant(),
            )

        @staticmethod
        async def backfill_batches(
            _channel_id, _after_message_id, _batch_size
        ) -> AsyncIterator[list[RawTelegramMessage]]:
            yield []

        @staticmethod
        async def live_message_ids(_channel_id) -> set[int]:
            return set()

        @staticmethod
        async def live_events(_channel_ids) -> AsyncIterator[TelegramDeliveryEvent]:
            yield TelegramDeliveryEvent(
                message=_message(),
                mode=DeliveryMode.PUSH,
                captured_at=_instant(),
                gap_closed=False,
            )

    assert isinstance(FakeSource(), TelegramSource)


def test_source_missing_resolve_channel_does_not_satisfy_protocol():
    class NoResolve:
        @staticmethod
        async def backfill_batches(_channel_id, _after_message_id, _batch_size):
            yield []

        @staticmethod
        async def live_events(_channel_ids):
            yield None

    assert not isinstance(NoResolve(), TelegramSource)


def test_source_missing_live_events_does_not_satisfy_protocol():
    class BackfillOnly:
        @staticmethod
        async def backfill_batches(_channel_id, _after_message_id, _batch_size):
            yield []

    assert not isinstance(BackfillOnly(), TelegramSource)


def test_source_missing_live_message_ids_does_not_satisfy_protocol():
    class NoLiveIds:
        @staticmethod
        async def resolve_channel(_reference) -> TelegramChannel:
            return TelegramChannel(
                channel_id=1, title="t", is_private=False, first_seen_at=_instant()
            )

        @staticmethod
        async def backfill_batches(_channel_id, _after_message_id, _batch_size):
            yield []

        @staticmethod
        async def live_events(_channel_ids):
            yield None

    assert not isinstance(NoLiveIds(), TelegramSource)


def test_telethon_source_satisfies_protocol():
    # structural conformance only (no client / no network)
    assert isinstance(TelethonSource(client=None), TelegramSource)


class FakeTelethonClient:
    def __init__(
        self,
        messages_by_channel: dict[int, list] | None = None,
        entities_by_reference: dict | None = None,
        dialogs: list | None = None,
    ) -> None:
        self.handlers = []
        self.messages_by_channel = messages_by_channel or {}
        self.entities_by_reference = entities_by_reference or {}
        self.dialogs = dialogs or []
        self.get_entity_calls = []
        self.iter_calls = []
        self.iter_dialog_calls = 0

    def add_event_handler(self, callback, event) -> None:
        self.handlers.append((callback, event))

    def remove_event_handler(self, callback, event) -> int:
        self.handlers = [item for item in self.handlers if item != (callback, event)]
        return 1

    async def get_entity(self, reference):
        self.get_entity_calls.append(reference)
        if reference in self.entities_by_reference:
            return self.entities_by_reference[reference]
        raise ValueError(f"Cannot find any entity corresponding to {reference!r}")

    async def __call__(self, request):
        return type("FullChannelResult", (), {"full_chat": _full_chat(1234)})()

    async def iter_dialogs(self):
        self.iter_dialog_calls += 1
        for dialog in self.dialogs:
            yield dialog

    async def iter_messages(self, channel_id, **kwargs):
        self.iter_calls.append((channel_id, kwargs))
        for message in self.messages_by_channel.get(channel_id, []):
            yield message

    async def emit_new_message(self, message) -> None:
        event = type("NewMessageEvent", (), {"message": message, "chat_id": 1})()
        callback, _ = self.handlers[0]
        await callback(event)

    async def emit_deleted_messages(self, message_ids: list[int]) -> None:
        event = type(
            "DeletedMessageEvent",
            (),
            {"deleted_ids": message_ids, "chat_id": 1, "chat_peer": None},
        )()
        callback, _ = self.handlers[1]
        await callback(event)


class FakeTelethonMessage:
    def __init__(self, message_id: int = 10) -> None:
        self.id = message_id
        self.message = "BTC long 65000"
        self.sender_id = 20
        self.date = _instant()
        self.reply_to_msg_id = None
        self.edit_date = None
        self.media = None
        self.views = 100
        self.forwards = 5

    def to_dict(self):
        return {"id": self.id, "message": self.message}


def _entity(entity_id: int = 7, title: str = "Pilot", username: str | None = "pilot"):
    return type(
        "FakeTelethonEntity",
        (),
        {"id": entity_id, "title": title, "username": username},
    )()


def _dialog(entity, name: str | None = None):
    return type("FakeTelethonDialog", (), {"entity": entity, "name": name})()


def _full_chat(participants_count: int):
    return type("FakeFullChat", (), {"participants_count": participants_count})()


async def test_resolve_channel_uses_canonical_handle_directly():
    entity = _entity(entity_id=7, title="Pilot", username="pilot")
    client = FakeTelethonClient(entities_by_reference={"@pilot": entity})

    channel = await TelethonSource(client).resolve_channel("@pilot")

    assert channel.channel_id == 7
    assert channel.title == "Pilot"
    assert channel.handle == "pilot"
    assert channel.subscriber_count == 1234
    assert client.get_entity_calls == ["@pilot"]
    assert client.iter_dialog_calls == 0


async def test_resolve_channel_uses_dialog_title_path_for_non_username_title():
    entity = _entity(
        entity_id=8,
        title="Математик. Трейдинг и инвестиции.",
        username=None,
    )
    client = FakeTelethonClient(dialogs=[_dialog(entity)])

    channel = await TelethonSource(client).resolve_channel(
        "Математик. Трейдинг и инвестиции."
    )

    assert channel.channel_id == 8
    assert channel.title == "Математик. Трейдинг и инвестиции."
    assert channel.handle is None
    assert client.get_entity_calls == []
    assert client.iter_dialog_calls == 1


async def test_resolve_channel_rejects_ambiguous_dialog_title():
    title = "Signals"
    client = FakeTelethonClient(
        dialogs=[
            _dialog(_entity(entity_id=7, title=title, username="one")),
            _dialog(_entity(entity_id=8, title=title, username="two")),
        ]
    )

    with pytest.raises(ChannelReferenceResolutionError, match="multiple"):
        await TelethonSource(client).resolve_channel(f"title:{title}")


async def test_resolve_channel_rejects_unknown_dialog_title():
    client = FakeTelethonClient(dialogs=[])

    with pytest.raises(ChannelReferenceResolutionError, match="No joined dialog"):
        await TelethonSource(client).resolve_channel("Unknown channel title")


async def test_telethon_live_events_yields_push_delivery():
    client = FakeTelethonClient()
    stream = TelethonSource(client).live_events([1])
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)

    await client.emit_new_message(FakeTelethonMessage())
    event = await pending
    await stream.aclose()

    assert isinstance(event, TelegramDeliveryEvent)
    assert event.mode is DeliveryMode.PUSH
    assert event.message.channel_id == 1
    assert event.message.message_id == 10
    assert event.message.text == "BTC long 65000"


async def test_telethon_live_events_yields_poll_catch_up_delivery():
    client = FakeTelethonClient({1: [FakeTelethonMessage(11)]})
    stream = TelethonSource(client).live_events([1])

    event = await anext(stream)
    await stream.aclose()

    assert isinstance(event, TelegramDeliveryEvent)
    assert event.mode is DeliveryMode.CATCH_UP
    assert event.gap_closed is True
    assert event.message.message_id == 11
    assert client.iter_calls[0] == (1, {"limit": 1})


async def test_telethon_live_events_yields_delete_notice():
    client = FakeTelethonClient()
    stream = TelethonSource(client).live_events([1])
    pending = asyncio.create_task(anext(stream))
    await asyncio.sleep(0)

    await client.emit_deleted_messages([10])
    event = await pending
    await stream.aclose()

    assert isinstance(event, TelegramDeletionEvent)
    assert event.channel_id == 1
    assert event.message_id == 10
