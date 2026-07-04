"""Parity port of ``scoring.test.js``."""

from verasig.features.rules.template_mining.directions import detect_directions
from verasig.features.rules.template_mining.fields import extract_signal_fields
from verasig.features.rules.template_mining.scoring import score_candidate


def _candidate_of(text: str) -> dict:
    return {
        "message": {"id": "t", "text": text},
        "fields": extract_signal_fields(text),
        "directions": detect_directions(text),
    }


# --- bounds ---
def test_always_returns_a_confidence_between_0_and_1():
    texts = [
        "XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355",
        "Move SL to BE on gold buy",
        "gm everyone",
        "XAUUSD BUY hit TP1 ✅",
    ]
    for text in texts:
        score = score_candidate(_candidate_of(text))
        assert score >= 0
        assert score <= 1


# --- ranking ---
def test_scores_a_complete_new_signal_highly():
    assert (
        score_candidate(_candidate_of("XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355"))
        > 0.7
    )


def test_scores_an_update_below_a_complete_new_signal():
    signal = score_candidate(_candidate_of("XAUUSD BUY NOW\nSL 2312\nTP 2340"))
    update = score_candidate(_candidate_of("Move SL to BE on gold buy"))
    assert update < signal
    assert update < 0.4


def test_scores_a_tp_hit_result_low():
    assert score_candidate(_candidate_of("XAUUSD BUY hit TP1 ✅")) < 0.4


def test_ranks_a_complete_signal_above_a_bare_directional_call():
    full = score_candidate(_candidate_of("XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355"))
    bare = score_candidate(_candidate_of("BTC long"))
    assert full > bare


def test_penalizes_an_emoji_only_direction_relative_to_a_worded_one():
    emoji_only = score_candidate(
        _candidate_of("\U0001f7e2 XAUUSD\nEntry 2320\nSL 2312\nTP 2340")
    )
    worded = score_candidate(_candidate_of("BUY XAUUSD\nEntry 2320\nSL 2312\nTP 2340"))
    assert emoji_only < worded
