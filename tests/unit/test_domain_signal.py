from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from verasig.domain.signal import (
    EntryType,
    ExtractedSignal,
    ExtractionMethod,
    Side,
    SignalEventType,
    UnrecognizedSignal,
)


def _signal(**overrides) -> ExtractedSignal:
    base = {
        "event_id": uuid4(),
        "channel_id": 1,
        "symbol": "BTCUSDT",
        "side": Side.LONG,
    }
    base.update(overrides)
    return ExtractedSignal(**base)


def test_extracted_signal_constructs_with_required_symbol_side_and_linkage():
    signal = _signal()
    assert signal.symbol == "BTCUSDT"
    assert signal.side is Side.LONG
    assert signal.channel_id == 1


def test_extracted_signal_defaults_provenance_and_optionals():
    signal = _signal()
    assert isinstance(signal.id, UUID)
    assert signal.event_type is SignalEventType.NEW_ENTRY
    assert signal.extraction_method is ExtractionMethod.DETERMINISTIC
    assert signal.parser_confidence == 1.0
    assert signal.take_profits == []
    assert signal.entry_type is None
    assert signal.stop_loss is None
    assert isinstance(signal.extracted_at, datetime)


def test_extracted_signal_rejects_empty_symbol():
    with pytest.raises(ValidationError):
        _signal(symbol="")


def test_extracted_signal_rejects_missing_side():
    with pytest.raises(ValidationError):
        ExtractedSignal(event_id=uuid4(), channel_id=1, symbol="BTCUSDT")


def test_extracted_signal_take_profits_are_ordered_decimals():
    signal = _signal(side=Side.SHORT, take_profits=["67000", "68000"])
    assert signal.take_profits == [Decimal("67000"), Decimal("68000")]


def test_unrecognized_signal_constructs_with_reason_and_defaults():
    unrecognized = UnrecognizedSignal(event_id=uuid4(), reason="no_match")
    assert unrecognized.reason == "no_match"
    assert isinstance(unrecognized.id, UUID)
    assert unrecognized.attempted_methods == []
    assert isinstance(unrecognized.created_at, datetime)


def test_side_has_long_and_short():
    assert {side.value for side in Side} == {"LONG", "SHORT"}


def test_entry_type_has_market_single_and_range():
    assert {entry.value for entry in EntryType} == {
        "MARKET",
        "LIMIT_SINGLE",
        "LIMIT_RANGE",
    }


def test_signal_event_type_has_the_four_lifecycle_values():
    assert {kind.value for kind in SignalEventType} == {
        "NEW_ENTRY",
        "MODIFY",
        "CLOSE",
        "UNRECOGNIZED",
    }


def test_extraction_method_has_deterministic_and_fallback():
    assert {method.value for method in ExtractionMethod} == {
        "DETERMINISTIC",
        "LLM_FALLBACK",
    }
