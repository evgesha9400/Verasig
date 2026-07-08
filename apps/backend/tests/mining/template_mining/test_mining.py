"""Parity port of ``mining.test.js``."""

from fixtures_sample_messages import SIGNAL_FAMILY as SIGNALS

from verasig.features.mining.template_mining.mining import mine_template_groups

RESULTS = [
    {"id": "r1", "date": "2026-06-01", "text": "XAUUSD BUY hit TP1"},
    {"id": "r2", "date": "2026-06-02", "text": "EURUSD SELL hit TP1"},
]
NOISE = [
    {"id": "n1", "text": "gm team, choppy open"},
    {"id": "n2", "text": "join our VIP tier, link in bio"},
]


def _mine():
    return mine_template_groups([*SIGNALS, *RESULTS, *NOISE])


def test_only_forms_families_from_new_signal_candidates():
    groups = _mine()
    total = sum(group.count for group in groups)
    assert total == len(SIGNALS)


def test_groups_structurally_identical_signals_into_one_family():
    groups = _mine()
    signal_group = next(g for g in groups if g.count == len(SIGNALS))
    assert "<INSTRUMENT> <SIDE> MARKET" in signal_group.normalized_template


def test_suggests_accepting_a_clean_high_confidence_new_signal_family():
    groups = _mine()
    signal_group = next(g for g in groups if g.count == len(SIGNALS))
    assert signal_group.suggested_action == "accept"
    assert signal_group.confidence_avg > 0.6
    assert signal_group.intent_distribution["new_signal"] == len(SIGNALS)
    assert signal_group.status == "unreviewed"


def test_does_not_turn_update_result_messages_into_template_families():
    groups = _mine()
    assert not any("HIT" in group.normalized_template for group in groups)


def test_computes_a_date_range_from_message_dates():
    groups = _mine()
    signal_group = next(g for g in groups if g.count == len(SIGNALS))
    assert signal_group.date_range == {"from": "2026-06-01", "to": "2026-06-03"}


def test_limits_examples_to_at_most_five_per_group():
    groups = _mine()
    for group in groups:
        assert len(group.examples) <= 5
        assert len(group.examples) > 0


def test_sorts_groups_by_count_descending():
    groups = _mine()
    counts = [group.count for group in groups]
    assert counts == sorted(counts, reverse=True)


# --- overlay teaches unknown coin + token ---
def test_mines_a_signal_that_only_parses_once_the_overlay_teaches_coin_and_token():
    message = {
        "id": "x1",
        "text": "АПТ \U0001f680\nEntry: 2.50\nStop: 2.40\nTarget: 2.70",
    }
    overlay = {
        "instrumentAliases": {"АПТ": "APTUSDT"},
        "directionTokens": {"\U0001f680": "BUY"},
    }
    with_overlay = mine_template_groups([message], overlay)
    instruments = [c.fields.instrument for g in with_overlay for c in g.candidates]
    assert "APTUSDT" in instruments


# --- geometry-broken families never auto-accept ---
def test_downgrades_a_stop_target_inverted_family_to_review():
    broken = [
        {"id": "g1", "text": "XAUUSD BUY\nEntry 2320\nSL 2340\nTP 2300"},
        {"id": "g2", "text": "XAUUSD BUY\nEntry 2321\nSL 2341\nTP 2301"},
    ]
    group = mine_template_groups(broken)[0]
    assert group.geometry_warnings == len(broken)
    assert group.suggested_action == "review"
