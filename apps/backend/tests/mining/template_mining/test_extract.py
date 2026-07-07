"""Parity port of ``extract.test.js``."""

import re

from verasig.features.mining.template_mining.extract import attempt_extract_signal


# --- the parser is the classifier ---
def test_returns_none_when_there_is_no_instrument_and_no_direction():
    assert (
        attempt_extract_signal(
            {"id": "1", "text": "Good morning team, waiting for NY session"}
        )
        is None
    )


def test_returns_none_when_an_instrument_has_no_direction():
    assert (
        attempt_extract_signal(
            {"id": "1", "text": "XAUUSD analysis: price may reject from 2330"}
        )
        is None
    )


def test_accepts_a_raw_string_and_wraps_it_into_a_candidate():
    candidate = attempt_extract_signal("BUY XAUUSD NOW\nSL 2312")
    assert candidate is not None
    assert "XAUUSD" in candidate.message.text


# --- full new signal ---
def test_extracts_the_structured_fields():
    candidate = attempt_extract_signal(
        {"id": "m1", "text": "XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355"}
    )
    assert candidate.fields.instrument == "XAUUSD"
    assert candidate.fields.direction == "BUY"
    assert candidate.fields.order_type == "market"
    assert candidate.fields.entry is None
    assert candidate.fields.stop_loss == 2312
    assert candidate.fields.take_profits == [2340, 2355]


def test_classifies_intent_as_new_signal_with_high_confidence_and_no_rejections():
    candidate = attempt_extract_signal(
        {"id": "m1", "text": "XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355"}
    )
    assert candidate.intent == "new_signal"
    assert candidate.confidence > 0.7
    assert len(candidate.rejection_reasons) == 0


def test_carries_a_normalized_template_and_key():
    candidate = attempt_extract_signal(
        {"id": "m1", "text": "XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355"}
    )
    assert re.match(r"^tpl_", candidate.template_key)
    assert "<INSTRUMENT>" in candidate.normalized_template


# --- range signal ---
def test_parses_a_eurusd_range_sell():
    candidate = attempt_extract_signal(
        {"id": "m2", "text": "Sell EURUSD 1.0860-1.0870\nSL 1.0900\nTP 1.0800"}
    )
    assert candidate.fields.order_type == "range"
    assert candidate.fields.entry.type == "range"
    assert candidate.fields.entry.min == 1.086
    assert candidate.fields.entry.max == 1.087
    assert candidate.intent == "new_signal"


# --- only new signals are candidates ---
def test_returns_none_for_a_result_hit_tp():
    assert attempt_extract_signal({"id": "m3", "text": "XAUUSD BUY hit TP1"}) is None


def test_returns_none_for_an_update_stop_move():
    assert (
        attempt_extract_signal({"id": "m4", "text": "Move SL to BE on gold buy"})
        is None
    )


def test_returns_none_for_directional_commentary_with_no_structure():
    assert (
        attempt_extract_signal(
            {
                "id": "m6",
                "text": (
                    "The whale stays long on BTC across every exchange "
                    "while volume keeps climbing steadily"
                ),
            }
        )
        is None
    )


# --- suspicious geometry is flagged, not dropped ---
def test_flags_reversed_stop_target_placement():
    candidate = attempt_extract_signal(
        {"id": "m5", "text": "BUY XAUUSD 2320\nSL 2340\nTP 2310"}
    )
    assert candidate is not None
    assert any(
        re.search(r"stop|target|entry", reason, re.IGNORECASE)
        for reason in candidate.rejection_reasons
    )
