from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from verasig.domain.channel import TelegramChannel


def _instant() -> datetime:
    return datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)


def test_channel_constructs_with_required_fields():
    channel = TelegramChannel(
        channel_id=784175081,
        title="Pilot Signals",
        is_private=False,
        first_seen_at=_instant(),
    )
    assert channel.channel_id == 784175081
    assert channel.title == "Pilot Signals"


def test_channel_defaults_optionals_to_none():
    channel = TelegramChannel(
        channel_id=1,
        title="x",
        is_private=True,
        first_seen_at=_instant(),
    )
    assert channel.handle is None
    assert channel.subscriber_count is None
    assert channel.captured_through_message_id is None


def test_channel_rejects_missing_title():
    with pytest.raises(ValidationError):
        TelegramChannel(channel_id=1, is_private=False, first_seen_at=_instant())
