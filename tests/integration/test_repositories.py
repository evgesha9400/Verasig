from datetime import datetime, timezone

from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage
from verasig.storage import repositories as repo
from verasig.storage.models import ChannelRow


def _instant() -> datetime:
    return datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)


def _channel(**overrides) -> TelegramChannel:
    base = {
        "channel_id": 1,
        "title": "Pilot",
        "is_private": False,
        "first_seen_at": _instant(),
    }
    base.update(overrides)
    return TelegramChannel(**base)


def _message(message_id: int, channel_id: int = 1) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=channel_id,
        message_id=message_id,
        posted_at=_instant(),
        captured_at=_instant(),
        has_media=False,
        raw_payload={"id": message_id},
    )


def test_insert_messages_dedups_on_conflict(db_session):
    repo.upsert_channel(db_session, _channel())
    db_session.commit()
    inserted_first = repo.insert_messages(db_session, [_message(1), _message(2)])
    db_session.commit()
    inserted_again = repo.insert_messages(db_session, [_message(2), _message(3)])
    db_session.commit()
    assert inserted_first == 2
    assert inserted_again == 1
    assert repo.count_messages(db_session, 1) == 3


def test_advance_cursor_is_monotonic(db_session):
    repo.upsert_channel(db_session, _channel())
    db_session.commit()
    repo.advance_cursor(db_session, 1, 50)
    db_session.commit()
    repo.advance_cursor(db_session, 1, 30)
    db_session.commit()
    assert repo.read_cursor(db_session, 1) == 50


def test_read_cursor_is_none_for_unknown_channel(db_session):
    assert repo.read_cursor(db_session, 999) is None


def test_upsert_channel_updates_metadata_but_preserves_first_seen_and_cursor(
    db_session,
):
    repo.upsert_channel(db_session, _channel(subscriber_count=100))
    db_session.commit()
    repo.advance_cursor(db_session, 1, 42)
    db_session.commit()

    later = datetime(2027, 1, 1, tzinfo=timezone.utc)
    repo.upsert_channel(
        db_session,
        _channel(title="Renamed", subscriber_count=200, first_seen_at=later),
    )
    db_session.commit()

    channel = db_session.get(ChannelRow, 1)
    assert channel.title == "Renamed"
    assert channel.subscriber_count == 200
    assert channel.first_seen_at == _instant()
    assert repo.read_cursor(db_session, 1) == 42
