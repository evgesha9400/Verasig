"""Unit tests for the Verify audit categorizer (parity port of ``rules.test.js``).

``compute_audit`` is the pure function the ``/mining/audit`` route wraps: given
the feed's messages, its freshly-mined groups, and the operator's accepted
template keys, it reproduces the SAME bucketing the browser's
``applyAcceptedRules`` used to compute client-side.
"""

from verasig.features.mining.mining_audit import _derive_threshold, compute_audit
from verasig.features.mining.template_mining import mine_template_groups
from verasig.features.mining.template_mining.types import ChatMessage

SIGNAL_FAMILY = [
    ChatMessage(
        id="s1", date="2026-06-01", text="XAUUSD BUY NOW\nSL 2312\nTP 2340\nTP 2355"
    ),
    ChatMessage(
        id="s2", date="2026-06-02", text="XAUUSD BUY NOW\nSL 2305\nTP 2330\nTP 2350"
    ),
    ChatMessage(
        id="s3", date="2026-06-03", text="XAUUSD BUY NOW\nSL 2300\nTP 2325\nTP 2345"
    ),
]
# A single-line, inline-labelled shape — structurally distinct from
# SIGNAL_FAMILY's multi-line block, so it mines into its own family.
OTHER_FAMILY = [
    ChatMessage(id="o1", date="2026-06-06", text="BTC LONG entry 100 sl 95 tp 110"),
    ChatMessage(id="o2", date="2026-06-07", text="ETH LONG entry 200 sl 190 tp 210"),
]
RESULT_MESSAGE = ChatMessage(id="r1", date="2026-06-04", text="XAUUSD BUY hit TP1")
NOISE_MESSAGE = ChatMessage(id="n1", date="2026-06-05", text="gm team, choppy open")

ALL_MESSAGES = [*SIGNAL_FAMILY, RESULT_MESSAGE, NOISE_MESSAGE, *OTHER_FAMILY]


def _mine():
    return mine_template_groups(ALL_MESSAGES)


def _signal_group(groups):
    return next(group for group in groups if group.count == len(SIGNAL_FAMILY))


def _other_group(groups):
    return next(group for group in groups if group.count == len(OTHER_FAMILY))


def test_accepted_family_parses_every_member_as_an_exact_match():
    groups = _mine()
    signal_group = _signal_group(groups)

    audit = compute_audit(ALL_MESSAGES, groups, [signal_group.template_key])

    assert len(audit.parsed_signals) == len(SIGNAL_FAMILY)
    assert {s.source_message_ids[0] for s in audit.parsed_signals} == {
        m.id for m in SIGNAL_FAMILY
    }
    assert all(s.match == "exact" for s in audit.parsed_signals)
    expected_rule_id = f"rule_{signal_group.template_key.removeprefix('tpl_')}"
    assert all(s.parser_rule_id == expected_rule_id for s in audit.parsed_signals)
    assert audit.ambiguous_candidates == []


def test_unaccepted_family_falls_to_rare_templates():
    groups = _mine()
    signal_group = _signal_group(groups)
    other_group = _other_group(groups)

    audit = compute_audit(ALL_MESSAGES, groups, [signal_group.template_key])

    assert any(
        rare.template_key == other_group.template_key for rare in audit.rare_templates
    )
    assert sum(rare.count for rare in audit.rare_templates) == len(OTHER_FAMILY)


def test_result_message_is_rejected_without_becoming_a_family():
    groups = _mine()
    signal_group = _signal_group(groups)

    audit = compute_audit(ALL_MESSAGES, groups, [signal_group.template_key])

    rejected_ids = {entry.message.id for entry in audit.rejected_candidates}
    assert RESULT_MESSAGE.id in rejected_ids
    result_entry = next(
        entry
        for entry in audit.rejected_candidates
        if entry.message.id == RESULT_MESSAGE.id
    )
    assert result_entry.intent == "result"


def test_noise_message_lands_in_no_bucket():
    groups = _mine()
    signal_group = _signal_group(groups)

    audit = compute_audit(ALL_MESSAGES, groups, [signal_group.template_key])

    seen_ids = (
        {s.source_message_ids[0] for s in audit.parsed_signals}
        | {c.message.id for c in audit.ambiguous_candidates}
        | {entry.message.id for entry in audit.rejected_candidates}
        | {m.id for m in audit.potential_misses}
    )
    assert NOISE_MESSAGE.id not in seen_ids


def test_overlay_threshold_override_demotes_the_family_to_ambiguous():
    groups = _mine()
    signal_group = _signal_group(groups)
    overlay = {"templateThresholds": {signal_group.template_key: 0.999}}

    audit = compute_audit(
        ALL_MESSAGES, groups, [signal_group.template_key], overlay=overlay
    )

    assert audit.parsed_signals == []
    assert len(audit.ambiguous_candidates) == len(SIGNAL_FAMILY)


def test_overlay_reject_phrase_reroutes_an_otherwise_parsed_family():
    groups = _mine()
    signal_group = _signal_group(groups)
    overlay = {"rejectPhrases": ["xauusd buy now"]}

    audit = compute_audit(
        ALL_MESSAGES, groups, [signal_group.template_key], overlay=overlay
    )

    assert audit.parsed_signals == []
    rejected_ids = {entry.message.id for entry in audit.rejected_candidates}
    assert rejected_ids >= {m.id for m in SIGNAL_FAMILY}


def test_reject_phrase_matches_across_a_non_breaking_space():
    groups = _mine()
    signal_group = _signal_group(groups)
    overlay = {"rejectPhrases": ["xauusd buy"]}
    spaced = ChatMessage(id="s4", text="XAUUSD\u00a0BUY NOW\nSL 2300\nTP 2325\nTP 2345")

    audit = compute_audit([spaced], groups, [signal_group.template_key], overlay)

    assert [entry.message.id for entry in audit.rejected_candidates] == ["s4"]


def test_no_accepted_keys_yields_an_empty_audit_with_everything_rare_or_rejected():
    groups = _mine()

    audit = compute_audit(ALL_MESSAGES, groups, [])

    assert audit.parsed_signals == []
    assert audit.ambiguous_candidates == []
    total_candidates_recovered = sum(group.count for group in audit.rare_templates)
    assert total_candidates_recovered == len(SIGNAL_FAMILY) + len(OTHER_FAMILY)


def test_derive_threshold_stays_within_bounds():
    assert _derive_threshold(0.95) == 0.85
    assert _derive_threshold(0.5) == 0.5  # 0.5 - 0.1 = 0.4, clamped up to the floor
    assert _derive_threshold(1.0) == 0.9
