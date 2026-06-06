from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import DeletionConfidence, DeletionMethod
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.message import DeliveryMode, RawTelegramMessage
from verasig.foundation.telegram_source import (
    TelegramDeletionEvent,
    TelegramDeliveryEvent,
    TelegramLiveEvent,
)
from verasig.services.ingestion.live import ingest_live
from verasig.storage import repositories as repo

_CHANNEL_ID = 7
_POSTED = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


class FakeLiveSource:
    def __init__(self, events: list[TelegramLiveEvent]) -> None:
        self.events = events
        self.requested_channel_ids: list[list[int]] = []

    def live_events(self, channel_ids: list[int]) -> AsyncIterator[TelegramLiveEvent]:
        async def _events() -> AsyncIterator[TelegramLiveEvent]:
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


def _deletion(message_id: int, detected_at: datetime) -> TelegramDeletionEvent:
    return TelegramDeletionEvent(
        channel_id=_CHANNEL_ID,
        message_id=message_id,
        detected_at=detected_at,
    )


def _seed_channel(session_factory) -> None:
    with session_factory() as session:
        repo.upsert_channel(session, _channel())
        session.commit()


def _seed_captured_signal(session_factory, message: RawTelegramMessage) -> None:
    with session_factory() as session:
        repo.upsert_channel(session, _channel())
        repo.insert_messages(session, [message])
        repo.insert_signal_events(
            session,
            [
                RawSignalEvent(
                    channel_id=_CHANNEL_ID,
                    message_id=message.message_id,
                    candidate_text=message.text or "",
                    materialized_by=MaterializationPath.SEED_HEURISTIC,
                )
            ],
        )
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


async def test_live_ingestion_dedupes_catch_up_against_backfilled_row(
    session_factory,
):
    captured_at = _POSTED + timedelta(seconds=1)
    _seed_captured_signal(session_factory, _message(10, captured_at))
    source = FakeLiveSource(
        [_delivery(10, DeliveryMode.CATCH_UP, _POSTED + timedelta(seconds=4))]
    )

    result = await ingest_live(source, [_CHANNEL_ID], session_factory)

    assert result.inserted == 0
    assert result.duplicates == 1
    assert result.captured_by_mode == {}
    with session_factory() as session:
        messages = repo.read_messages(session, _CHANNEL_ID)
    assert len(messages) == 1
    assert messages[0].captured_at == captured_at


async def test_live_ingestion_persists_confirmed_delete_event_with_stored_text(
    session_factory,
):
    captured_at = _POSTED + timedelta(seconds=1)
    detected_at = _POSTED + timedelta(seconds=5)
    _seed_captured_signal(session_factory, _message(10, captured_at))
    source = FakeLiveSource([_deletion(10, detected_at)])

    result = await ingest_live(source, [_CHANNEL_ID], session_factory)

    assert result.deleted == 1
    with session_factory() as session:
        evidence = repo.read_deletion_evidence(session, _CHANNEL_ID)
    assert len(evidence) == 1
    assert evidence[0].confidence is DeletionConfidence.CONFIRMED
    assert evidence[0].method is DeletionMethod.LIVE_EVENT
    assert evidence[0].message_id == 10
    assert evidence[0].original_text == "BTC long 65000"
    assert evidence[0].first_seen_at == captured_at
    assert evidence[0].detected_at == detected_at
    assert evidence[0].was_signal_candidate is True
