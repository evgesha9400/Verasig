"""Parity port of ``fields.test.js``."""

from verasig.features.rules.template_mining.fields import extract_signal_fields


# --- instrument & direction ---
def test_normalizes_instrument_and_preserves_the_raw_alias():
    fields = extract_signal_fields("GOLD long now")
    assert fields.instrument == "XAUUSD"
    assert fields.instrument_raw.lower() == "gold"
    assert fields.direction == "BUY"


def test_chooses_a_word_direction_over_an_ambiguous_emoji():
    assert extract_signal_fields("\U0001f534 EURUSD sell 1.0860").direction == "SELL"


# --- entry & order type ---
def test_treats_now_as_a_market_order_with_no_entry():
    fields = extract_signal_fields("BUY XAUUSD NOW")
    assert fields.entry is None
    assert fields.order_type == "market"


def test_reads_at_price_as_a_single_limit_entry():
    fields = extract_signal_fields("BUY XAUUSD @ 2320")
    assert fields.entry.type == "single"
    assert fields.entry.price == 2320
    assert fields.order_type == "limit"


def test_reads_a_labelled_entry_range():
    fields = extract_signal_fields("XAUUSD BUY\nEntry: 2320-2325")
    assert fields.entry.type == "range"
    assert fields.entry.min == 2320
    assert fields.entry.max == 2325
    assert fields.order_type == "range"


def test_reads_a_zone_entry_range():
    fields = extract_signal_fields("NAS100 SELL ZONE 19800-19850")
    assert fields.instrument == "NAS100"
    assert fields.direction == "SELL"
    assert fields.entry.type == "range"
    assert fields.entry.min == 19800
    assert fields.entry.max == 19850
    assert fields.order_type == "range"


def test_reads_an_inline_header_price_as_the_entry():
    fields = extract_signal_fields("SHORT DOGE/USDT 0.1620")
    assert fields.entry.type == "single"
    assert fields.entry.price == 0.162


def test_assumes_a_market_order_when_no_entry_is_present():
    fields = extract_signal_fields("BTC LONG\nSL 67400\nTP 69000")
    assert fields.entry is None
    assert fields.order_type == "market"


# --- stop loss ---
def test_reads_an_sl_label():
    assert extract_signal_fields("XAUUSD BUY\nSL 2310").stop_loss == 2310


def test_reads_a_stop_below_label():
    assert extract_signal_fields("GOLD long\nStop below 2310").stop_loss == 2310


def test_reads_an_invalidation_label():
    assert extract_signal_fields("NAS100 sell\nInvalidation 19920").stop_loss == 19920


def test_does_not_read_a_risk_percentage_as_a_stop():
    assert (
        extract_signal_fields("LONG SOL/USDT 148.5\nRisk 2% of book").stop_loss is None
    )


def test_does_not_read_a_bare_risk_sizing_number_as_a_stop():
    fields = extract_signal_fields("XAUUSD buy\nEntry 2320\nRisk 50 Reward 150")
    assert fields.stop_loss is None


# --- take profits ---
def test_reads_a_single_tp():
    assert extract_signal_fields("XAUUSD BUY\nTP 2340").take_profits == [2340]


def test_accumulates_numbered_tp_lines_in_order():
    fields = extract_signal_fields("XAUUSD BUY\nTP1 2340\nTP2 2355\nTP3 2370")
    assert fields.take_profits == [2340, 2355, 2370]


def test_reads_a_target_list_on_one_line():
    fields = extract_signal_fields("GOLD long\nTargets 2340 / 2355 / 2370")
    assert fields.take_profits == [2340, 2355, 2370]


def test_recognises_a_multi_digit_target_index_like_tp10():
    fields = extract_signal_fields("XAUUSD BUY\nTP1 2340\nTP10 2500")
    assert fields.take_profits == [2340, 2500]


# --- full signals ---
def test_parses_a_market_xau_signal_with_two_tp_lines():
    fields = extract_signal_fields("XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355")
    assert fields.instrument == "XAUUSD"
    assert fields.direction == "BUY"
    assert fields.order_type == "market"
    assert fields.entry is None
    assert fields.stop_loss == 2312
    assert fields.take_profits == [2340, 2355]


def test_parses_a_eurusd_range_sell_signal():
    fields = extract_signal_fields("Sell EURUSD 1.0860-1.0870\nSL 1.0900\nTP 1.0800")
    assert fields.instrument == "EURUSD"
    assert fields.direction == "SELL"
    assert fields.order_type == "range"
    assert fields.stop_loss == 1.09
    assert fields.take_profits == [1.08]
    assert fields.entry.type == "range"
    assert fields.entry.min == 1.086
    assert fields.entry.max == 1.087


def test_accepts_a_chat_message_object_as_input():
    fields = extract_signal_fields({"id": "x", "text": "BUY XAUUSD NOW\nSL 2312"})
    assert fields.instrument == "XAUUSD"
    assert fields.stop_loss == 2312
