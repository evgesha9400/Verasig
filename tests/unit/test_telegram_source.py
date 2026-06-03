from collections.abc import AsyncIterator
from datetime import datetime, timezone

from verasig.domain.message import DeliveryMode, RawTelegramMessage
from verasig.foundation.telegram_source import TelegramDeliveryEvent, TelegramSource


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
        async def backfill_batches(
            self, channel_id, after_message_id, batch_size
        ) -> AsyncIterator[list[RawTelegramMessage]]:
            yield []

        async def live_events(
            self, channel_ids
        ) -> AsyncIterator[TelegramDeliveryEvent]:
            yield TelegramDeliveryEvent(
                message=_message(),
                mode=DeliveryMode.PUSH,
                captured_at=_instant(),
                gap_closed=False,
            )

    assert isinstance(FakeSource(), TelegramSource)


def test_source_missing_live_events_does_not_satisfy_protocol():
    class BackfillOnly:
        async def backfill_batches(self, channel_id, after_message_id, batch_size):
            yield []

    assert not isinstance(BackfillOnly(), TelegramSource)
