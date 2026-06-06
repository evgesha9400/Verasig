from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

from verasig.domain.channel import TelegramChannel
from verasig.domain.message import DeliveryMode, RawTelegramMessage
from verasig.foundation.telegram_source import TelegramDeliveryEvent
from verasig.services.ingestion.live import ingest_live
from verasig.storage import repositories as repo

_CHANNEL_ID = 7
_POSTED = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


class FakeLiveSource:
    def __init__(self, events: list[TelegramDeliveryEvent]) -> None:
        self.events = events
        self.requested_channel_ids: list[list[int]] = []

    def live_events(
        self, channel_ids: list[int]
    ) -> AsyncIterator[TelegramDeliveryEvent]:
        async def _events() -> AsyncIterator[TelegramDeliveryEvent]:
            self.requested_channel_ids.append(channel_ids)
            for event in self.events:
                yield event

        return _events()


def _channel() -> TelegramChannel:
    return TelegramChannel(
        channel_id=_CHANNEL_ID,
        handle="pilot",
        title="Pilot",
        is_private=False,
        first_seen_at=_POSTED,
    )


def _message(message_id: int, captured_at: datetime) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=_CHANNEL_ID,
        message_id=message_id,
        text="BTC long 65000",
        posted_at=_POSTED,
        captured_at=captured_at,
        has_media=False,
        raw_payload={"id": message_id},
    )


def _delivery(
    message_id: int, mode: DeliveryMode, captured_at: datetime
) -> TelegramDeliveryEvent:
    return TelegramDeliveryEvent(
        message=_message(message_id, captured_at),
        mode=mode,
        captured_at=captured_at,
        gap_closed=mode is not DeliveryMode.PUSH,
    )


def _seed_channel(session_factory) -> None:
    with session_factory() as session:
        repo.upsert_channel(session, _channel())
        session.commit()


async def test_live_ingestion_persists_push_and_dedupes_later_poll(
    session_factory,
):
    _seed_channel(session_factory)
    push_at = _POSTED + timedelta(seconds=1)
    poll_at = _POSTED + timedelta(seconds=3)
    source = FakeLiveSource(
        [
            _delivery(10, DeliveryMode.PUSH, push_at),
            _delivery(10, DeliveryMode.POLL, poll_at),
        ]
    )

    result = await ingest_live(source, [_CHANNEL_ID], session_factory)

    assert result.inserted == 1
    assert result.duplicates == 1
    assert result.captured_by_mode == {DeliveryMode.PUSH: 1}
    assert source.requested_channel_ids == [[_CHANNEL_ID]]
    with session_factory() as session:
        messages = repo.read_messages(session, _CHANNEL_ID)
    assert [message.message_id for message in messages] == [10]
    assert messages[0].captured_at == push_at
