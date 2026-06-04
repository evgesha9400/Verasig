from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from verasig.domain.drift import FilterDriftWarning, MissDiscoveredBy
from verasig.domain.label import GoldenLabel
from verasig.domain.signal import ExtractedSignal, Side


def test_golden_label_constructs_with_is_signal_and_defaults():
    label = GoldenLabel(channel_id=1, message_id=2, is_signal=False)
    assert label.is_signal is False
    assert isinstance(label.id, UUID)
    assert label.expected is None
    assert isinstance(label.labeled_at, datetime)


def test_golden_label_carries_expected_signal_when_positive():
    expected = ExtractedSignal(
        event_id=uuid4(), channel_id=1, symbol="BTCUSDT", side=Side.LONG
    )
    label = GoldenLabel(channel_id=1, message_id=2, is_signal=True, expected=expected)
    assert label.expected.symbol == "BTCUSDT"


def test_golden_label_rejects_missing_is_signal():
    with pytest.raises(ValidationError):
        GoldenLabel(channel_id=1, message_id=2)


def test_filter_drift_warning_constructs_with_miss_source_and_defaults():
    warning = FilterDriftWarning(
        channel_id=1,
        message_id=2,
        miss_discovered_by=MissDiscoveredBy.PARSER_BACKFILL,
    )
    assert warning.miss_discovered_by is MissDiscoveredBy.PARSER_BACKFILL
    assert isinstance(warning.id, UUID)
    assert warning.filter_rule_version is None
    assert warning.event_id is None
    assert warning.source_label_id is None
    assert isinstance(warning.created_at, datetime)


def test_filter_drift_warning_links_late_materialized_event():
    event_id = uuid4()
    warning = FilterDriftWarning(
        channel_id=1,
        message_id=2,
        miss_discovered_by=MissDiscoveredBy.PARSER_BACKFILL,
        event_id=event_id,
        filter_rule_version=3,
    )
    assert warning.event_id == event_id
    assert warning.filter_rule_version == 3


def test_miss_discovered_by_has_the_three_discovery_paths():
    assert {who.value for who in MissDiscoveredBy} == {
        "PARSER_BACKFILL",
        "HUMAN_AUDIT",
        "LLM_FALLBACK",
    }
