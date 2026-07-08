from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from verasig.domain.signal import (
    EntryType,
    Side,
    Signal,
    SignalEventType,
    TradeIntent,
)


def test_trade_intent_constructs_with_symbol_and_side():
    intent = TradeIntent(symbol="BTCUSDT", side=Side.LONG)
    assert intent.symbol == "BTCUSDT"
    assert intent.side is Side.LONG


def test_trade_intent_normalizes_symbol_to_upper_and_appends_usdt():
    assert TradeIntent(symbol="btc", side=Side.LONG).symbol == "BTCUSDT"
    assert TradeIntent(symbol="ETHUSDT", side=Side.SHORT).symbol == "ETHUSDT"


def test_trade_intent_rejects_empty_symbol():
    with pytest.raises(ValidationError):
        TradeIntent(symbol="", side=Side.LONG)


def test_trade_intent_is_provenance_free():
    assert "channel_id" not in TradeIntent.model_fields
    assert "message_id" not in TradeIntent.model_fields


def test_signal_extends_trade_intent():
    assert issubclass(Signal, TradeIntent)


def test_signal_has_no_parser_confidence():
    assert "parser_confidence" not in Signal.model_fields


def test_signal_normalizes_symbol_via_inherited_validator():
    assert _signal(symbol="btc").symbol == "BTCUSDT"


def _signal(**overrides) -> Signal:
    base = {
        "channel_id": 1,
        "message_id": 2,
        "candidate_text": "BTC long entry 65k",
        "symbol": "BTCUSDT",
        "side": Side.LONG,
    }
    base.update(overrides)
    return Signal(**base)


def test_signal_constructs_with_required_symbol_side_and_linkage():
    signal = _signal()
    assert signal.symbol == "BTCUSDT"
    assert signal.side is Side.LONG
    assert signal.channel_id == 1
    assert signal.message_id == 2
    assert signal.candidate_text == "BTC long entry 65k"


def test_signal_defaults_provenance_and_optionals():
    signal = _signal()
    assert isinstance(signal.id, UUID)
    assert signal.event_type is SignalEventType.NEW_ENTRY
    assert signal.take_profits == []
    assert signal.entry_type is None
    assert signal.stop_loss is None
    assert isinstance(signal.extracted_at, datetime)


def test_signal_rejects_empty_symbol():
    with pytest.raises(ValidationError):
        _signal(symbol="")


def test_signal_rejects_missing_side():
    with pytest.raises(ValidationError):
        Signal(
            channel_id=1,
            message_id=2,
            candidate_text="BTC long entry 65k",
            symbol="BTCUSDT",
        )


def test_signal_take_profits_are_ordered_decimals():
    signal = _signal(side=Side.SHORT, take_profits=["67000", "68000"])
    assert signal.take_profits == [Decimal("67000"), Decimal("68000")]


def test_signal_has_no_extraction_method():
    # extraction is always deterministic; the constant field/enum are dropped.
    assert "extraction_method" not in Signal.model_fields


def test_side_has_long_and_short():
    assert {side.value for side in Side} == {"LONG", "SHORT"}


def test_entry_type_has_market_single_and_range():
    assert {entry.value for entry in EntryType} == {
        "MARKET",
        "LIMIT_SINGLE",
        "LIMIT_RANGE",
    }


def test_signal_event_type_has_the_three_lifecycle_values():
    assert {kind.value for kind in SignalEventType} == {
        "NEW_ENTRY",
        "MODIFY",
        "CLOSE",
    }
