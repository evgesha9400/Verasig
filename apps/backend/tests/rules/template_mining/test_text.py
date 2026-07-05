"""Parity port of ``text.test.js``."""

from verasig.features.rules.template_mining.text import normalize_message_text


def test_keeps_original_untouched_for_display():
    result = normalize_message_text("XAUUSD   BUY")
    assert result.original == "XAUUSD   BUY"


def test_collapses_repeated_whitespace_inside_a_line():
    result = normalize_message_text("XAUUSD    BUY   NOW")
    assert result.clean == "XAUUSD BUY NOW"


def test_normalizes_unicode_spaces_to_regular_space():
    result = normalize_message_text("BUY XAUUSD NOW")
    assert result.clean == "BUY XAUUSD NOW"


def test_strips_thousands_separators_inside_numbers():
    result = normalize_message_text("entry 68,500")
    assert result.clean == "entry 68500"


def test_strips_thousands_separators_across_multi_group_numbers():
    result = normalize_message_text("1,234,567")
    assert result.clean == "1234567"


def test_preserves_a_price_range_and_normalizes_its_dash():
    result = normalize_message_text("Entry 2320–2325")
    assert result.clean == "Entry 2320-2325"


def test_keeps_a_plain_hyphen_price_range_intact():
    result = normalize_message_text("2320-2325")
    assert result.clean == "2320-2325"


def test_exposes_a_lowercased_view_for_matching():
    result = normalize_message_text("GOLD Long Now")
    assert result.lower == "gold long now"


def test_splits_clean_text_into_trimmed_non_empty_lines():
    result = normalize_message_text("XAUUSD BUY\n\n  SL 2312  \nTP 2340")
    assert result.lines == ["XAUUSD BUY", "SL 2312", "TP 2340"]


def test_handles_emoji_without_dropping_the_direction_word():
    result = normalize_message_text("\U0001f7e2 GOLD LONG \U0001f680")
    assert "GOLD LONG" in result.clean
    assert "\U0001f7e2" in result.clean


def test_treats_empty_input_as_empty_output():
    result = normalize_message_text("")
    assert result.clean == ""
    assert result.lines == []
