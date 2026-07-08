"""Parity port of ``prices.test.js``."""

import pytest

from verasig.features.mining.template_mining.prices import detect_prices, parse_number


def _values(text: str) -> list:
    return [price.value for price in detect_prices(text)]


# --- parse_number ---
def test_parses_a_plain_integer():
    assert parse_number("2320") == 2320


def test_parses_a_decimal():
    assert parse_number("2320.50") == 2320.5


def test_parses_a_forex_price():
    assert parse_number("1.0865") == 1.0865


def test_parses_thousands_separators():
    assert parse_number("68,500") == 68500


def test_expands_a_k_suffix():
    assert parse_number("66.5k") == 66500


def test_expands_an_m_suffix():
    assert parse_number("1.2m") == 1200000


def test_parses_a_very_small_crypto_price():
    assert parse_number("0.0000118") == pytest.approx(0.0000118, abs=1e-12)


# --- single levels ---
def test_detects_a_single_integer_level():
    price = detect_prices("SL 2310")[0]
    assert price.value == 2310
    assert price.type == "single"


def test_detects_a_decimal_level():
    assert _values("entry 2320.50") == [2320.5]


def test_detects_a_forex_level():
    assert _values("@ 1.0865") == [1.0865]


def test_detects_a_level_written_with_thousands_separators():
    assert _values("entry 68,500") == [68500]


# --- ranges ---
def test_detects_a_hyphen_range_as_min_max():
    price = detect_prices("Entry 2320-2325")[0]
    assert price.type == "range"
    assert price.min == 2320
    assert price.max == 2325


def test_detects_a_spaced_hyphen_range():
    price = detect_prices("Entry 2320 - 2325")[0]
    assert price.type == "range"
    assert price.min == 2320
    assert price.max == 2325


def test_detects_a_to_range():
    price = detect_prices("Entry 2320 to 2325")[0]
    assert price.type == "range"
    assert price.min == 2320
    assert price.max == 2325


def test_orders_a_descending_range_as_min_max():
    price = detect_prices("Entry 64200 - 63750")[0]
    assert price.type == "range"
    assert price.min == 63750
    assert price.max == 64200


# --- lists and labels ---
def test_detects_a_slash_separated_target_list_as_separate_levels():
    assert _values("Targets 2340 / 2355 / 2370") == [2340, 2355, 2370]


def test_detects_space_separated_targets_as_separate_levels():
    assert _values("Targets 19720 19650 19500") == [19720, 19650, 19500]


def test_does_not_treat_the_ordinal_in_tp1_as_a_price():
    assert _values("TP1 2340") == [2340]


def test_detects_one_level_per_numbered_target_line():
    assert _values("TP1 2340\nTP2 2355\nTP3 2370") == [2340, 2355, 2370]


# --- exclusions ---
def test_ignores_clock_times():
    assert len(detect_prices("closed at 08:42")) == 0


def test_ignores_leverage_like_5_10x():
    assert len(detect_prices("Leverage 5-10x")) == 0


def test_ignores_pnl_units_like_300_pips():
    assert len(detect_prices("running +300 pips")) == 0


def test_ignores_point_counts_like_150_points():
    assert len(detect_prices("closed +150 points")) == 0


def test_keeps_a_price_followed_by_a_space_and_a_word_starting_with_x_pct():
    assert _values("Entry 2320 Xau zone") == [2320]


def test_ignores_a_clock_time_that_carries_seconds():
    assert len(detect_prices("filled at 08:42:15")) == 0


def test_skips_a_separated_target_ordinal_but_keeps_its_value():
    assert _values("TP 1 2340") == [2340]


def test_keeps_a_bare_target_value_that_is_not_an_ordinal():
    assert _values("TP 50") == [50]


def test_keeps_the_raw_token_for_display():
    price = detect_prices("SL 2310")[0]
    assert "2310" in price.raw
