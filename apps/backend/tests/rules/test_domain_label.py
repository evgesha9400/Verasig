from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from verasig.domain.label import GoldenLabel, LabelKind
from verasig.domain.signal import ExtractedSignal, Side


def test_golden_label_constructs_with_label_and_defaults():
    label = GoldenLabel(channel_id=1, message_id=2, label=LabelKind.NOISE)
    assert label.is_signal is False
    assert isinstance(label.id, UUID)
    assert label.expected is None
    assert isinstance(label.labeled_at, datetime)


def test_golden_label_carries_expected_signal_when_positive():
    expected = ExtractedSignal(
        event_id=uuid4(), channel_id=1, symbol="BTCUSDT", side=Side.LONG
    )
    label = GoldenLabel(
        channel_id=1, message_id=2, label=LabelKind.SIGNAL, expected=expected
    )
    assert label.is_signal is True
    assert label.expected.symbol == "BTCUSDT"


def test_golden_label_rejects_missing_label():
    with pytest.raises(ValidationError):
        GoldenLabel(channel_id=1, message_id=2)
