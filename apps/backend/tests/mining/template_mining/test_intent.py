"""Parity port of ``intent.test.js``."""

from verasig.features.mining.template_mining.fields import extract_signal_fields
from verasig.features.mining.template_mining.intent import classify_intent


def _intent_of(text: str) -> str:
    return classify_intent(text, extract_signal_fields(text))


# --- new signals ---
def test_classifies_a_full_market_signal_as_new_signal():
    assert _intent_of("XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355") == "new_signal"


def test_classifies_a_range_sell_signal_as_new_signal():
    assert _intent_of("Sell EURUSD 1.0860-1.0870\nSL 1.0900\nTP 1.0800") == "new_signal"


def test_classifies_a_no_entry_signal_with_risk_levels_as_new_signal():
    assert _intent_of("BTC LONG\nSL 67400\nTP 69000\nTP 70500") == "new_signal"


def test_complete_setup_stays_new_signal_despite_result_words():
    # completeness is decided before the result heuristic, so "targets ... hit" in
    # an otherwise complete fresh setup does not flip it to a result.
    assert (
        _intent_of("XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355\nlet targets get hit")
        == "new_signal"
    )


# --- results ---
def test_treats_a_tp_hit_as_a_result():
    assert _intent_of("XAUUSD BUY hit TP1 ✅") == "result"


def test_treats_an_sl_hit_as_a_result():
    assert _intent_of("ETH short hit SL") == "result"


def test_treats_a_closed_trade_with_points_as_a_result():
    assert _intent_of("US30 buy closed +150 points") == "result"


def test_treats_running_pips_as_a_result():
    assert _intent_of("BTC long running +300 pips") == "result"


# --- updates ---
def test_treats_moving_stop_to_break_even_as_an_update():
    assert _intent_of("Move SL to BE on gold buy") == "update"


def test_treats_a_close_command_as_an_update():
    assert _intent_of("Close BTC long now") == "update"


def test_treats_a_cancel_as_an_update():
    assert _intent_of("Cancel EURUSD sell") == "update"


# --- commentary ---
def test_treats_a_directional_opinion_without_structure_as_commentary():
    assert (
        _intent_of("Gold looks bullish today but wait for confirmation") == "commentary"
    )


def test_treats_analysis_without_a_direction_as_commentary():
    assert _intent_of("XAUUSD analysis: price may reject from 2330") == "commentary"


# --- does not over-reject new signals ---
def test_keeps_a_take_profit_signal_as_new_signal():
    assert _intent_of("XAUUSD BUY now, take profit 2340") == "new_signal"


def test_keeps_a_profit_target_signal_as_new_signal():
    assert _intent_of("XAUUSD BUY now, profit target 2340") == "new_signal"


def test_keeps_a_hold_above_entry_condition_as_new_signal():
    assert _intent_of("Buy gold, will hold above 2300") == "new_signal"


def test_keeps_a_secure_zone_signal_as_new_signal():
    assert _intent_of("XAUUSD BUY now secure 2300 zone") == "new_signal"


def test_still_treats_secured_profit_as_a_result():
    assert _intent_of("XAUUSD long secured profit today") == "result"


def test_still_treats_hold_the_position_as_an_update():
    assert _intent_of("Gold buy, hold the position into NY") == "update"


# --- a complete fresh setup with a management note is a new signal ---
def test_keeps_a_scalp_with_a_close_half_instruction_as_new_signal():
    assert (
        _intent_of(
            "SCALP ARB/USDT long 1.124\nTight stop 1.092\n"
            "Target 1.190\nClose half at 1.16"
        )
        == "new_signal"
    )


def test_keeps_a_market_setup_with_a_partial_close_note_as_new_signal():
    assert (
        _intent_of("BTC LONG NOW\nSL 67400\nTP 69000\nClose half at first target")
        == "new_signal"
    )


def test_still_treats_a_bare_close_command_as_an_update():
    assert _intent_of("Close BTC long now") == "update"


def test_still_treats_a_stop_move_as_an_update_even_with_restated_levels():
    assert _intent_of("Move SL to BE on gold buy, entry was 2320") == "update"
