"""Parity port of ``geometry.test.js``."""

from types import SimpleNamespace

from verasig.features.mining.template_mining.fields import (
    SignalEntry,
    StructuredFields,
    extract_signal_fields,
)
from verasig.features.mining.template_mining.geometry import validate_price_geometry


def _buy(**over) -> StructuredFields:
    base = {
        "direction": "BUY",
        "entry": None,
        "stop_loss": None,
        "take_profits": [],
    }
    base.update(over)
    return StructuredFields(**base)


def _sell(**over) -> StructuredFields:
    fields = _buy(**over)
    fields.direction = "SELL"
    return fields


# --- valid structures ---
def test_accepts_a_buy_with_stop_below_and_targets_above_entry():
    result = validate_price_geometry(
        _buy(
            entry=SignalEntry(type="single", price=2320),
            stop_loss=2312,
            take_profits=[2340, 2355],
        )
    )
    assert result.is_valid is True
    assert len(result.warnings) == 0
    assert result.score_adjustment > 0


def test_accepts_a_sell_with_stop_above_and_target_below_entry_range():
    result = validate_price_geometry(
        _sell(
            entry=SignalEntry(type="range", min=1.086, max=1.087),
            stop_loss=1.09,
            take_profits=[1.08],
        )
    )
    assert result.is_valid is True


def test_accepts_a_no_entry_buy_where_stop_sits_below_the_targets():
    result = validate_price_geometry(_buy(stop_loss=67400, take_profits=[69000, 70500]))
    assert result.is_valid is True
    assert result.score_adjustment > 0


# --- suspicious structures are downgraded, not rejected ---
def test_labels_a_buy_stop_loss_that_equals_entry():
    result = validate_price_geometry(
        _buy(
            entry=SignalEntry(type="single", price=0.3853),
            stop_loss=0.3853,
            take_profits=[0.3901],
        )
    )
    assert result.is_valid is False
    assert any(
        issue.code == "stop_loss_on_wrong_side"
        and issue.field == "stopLoss"
        and issue.label == "Stop loss equals entry"
        for issue in result.issues
    )


def test_labels_a_take_profit_on_the_wrong_side_of_entry():
    result = validate_price_geometry(
        _sell(
            entry=SignalEntry(type="single", price=3.4238),
            stop_loss=3.6562,
            take_profits=[3.764, 3.3494],
        )
    )
    assert result.is_valid is False
    assert any(
        issue.code == "take_profit_on_wrong_side"
        and issue.field == "takeProfits"
        and issue.label == "Take profit above entry for SHORT"
        and issue.price == 3.764
        for issue in result.issues
    )


def test_flags_a_buy_with_stop_above_entry_and_target_below_entry():
    result = validate_price_geometry(
        extract_signal_fields("BUY XAUUSD 2320\nSL 2340\nTP 2310")
    )
    assert result.is_valid is False
    assert len(result.warnings) > 0
    assert result.score_adjustment < 0


def test_flags_a_no_entry_sell_whose_stop_is_below_its_targets():
    result = validate_price_geometry(_sell(stop_loss=100, take_profits=[110, 120]))
    assert result.is_valid is False


def test_flags_a_buy_whose_stop_sits_inside_the_entry_range():
    result = validate_price_geometry(
        _buy(
            entry=SignalEntry(type="range", min=2320, max=2325),
            stop_loss=2322,
            take_profits=[2340],
        )
    )
    assert result.is_valid is False


# --- insufficient information is skipped ---
def test_returns_valid_with_no_adjustment_when_there_is_nothing_to_compare():
    result = validate_price_geometry(_buy())
    assert result.is_valid is True
    assert result.score_adjustment == 0
    assert len(result.warnings) == 0


def test_skips_a_market_order_that_has_only_a_stop_and_no_targets():
    result = validate_price_geometry(_buy(stop_loss=2312))
    assert result.is_valid is True
    assert result.score_adjustment == 0


def test_accepts_a_candidate_wrapper_exposing_fields():
    result = validate_price_geometry(
        SimpleNamespace(
            fields=_buy(
                entry=SignalEntry(type="single", price=2320),
                stop_loss=2312,
                take_profits=[2340],
            )
        )
    )
    assert result.is_valid is True
