from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from verasig.domain.message import DeliveryMode, RawTelegramMessage


def _instant() -> datetime:
    return datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)


def test_raw_message_constructs_with_required_fields():
    message = RawTelegramMessage(
        channel_id=1,
        message_id=2,
        posted_at=_instant(),
        captured_at=_instant(),
        has_media=False,
        raw_payload={"id": 2},
    )
    assert (message.channel_id, message.message_id) == (1, 2)


def test_raw_message_defaults_optionals_to_none():
    message = RawTelegramMessage(
        channel_id=1,
        message_id=2,
        posted_at=_instant(),
        captured_at=_instant(),
        has_media=False,
        raw_payload={},
    )
    assert message.text is None
    assert message.sender_id is None
    assert message.reply_to_message_id is None
    assert message.views is None


def test_raw_message_rejects_missing_core_fields():
    with pytest.raises(ValidationError):
        RawTelegramMessage(message_id=2)


def test_delivery_mode_has_the_three_latency_provenance_values():
    assert {mode.value for mode in DeliveryMode} == {"PUSH", "POLL", "CATCH_UP"}
