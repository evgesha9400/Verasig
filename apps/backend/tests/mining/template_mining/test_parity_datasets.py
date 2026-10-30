"""End-to-end golden anchor: the miner over the bundled datasets.

Runs ``mine_template_groups`` over SAMPLE_MESSAGES and FEED_MESSAGES and asserts
the exact template families (keys, counts, normalized templates, suggested
actions, confidence ordering). The values were first captured from the retired
JS miner; the backend now owns the miner, so they pin its canonical skeletons
(one-target-per-line runs collapse to ``TP <PRICE_LIST>``, leverage ranges to
``<LEVERAGE>``).

The expected normalized-template strings are verbatim skeletons, so E501 is
waived file-wide rather than wrapping (and risking altering) them.
"""
# ruff: noqa: E501

from __future__ import annotations

from fixtures_feed_messages import FEED_MESSAGES
from fixtures_sample_messages import SAMPLE_MESSAGES

from verasig.features.mining.template_mining.mining import mine_template_groups

# (template_key, normalized_template, count, confidence_avg, suggested_action,
#  geometry_warnings) - ordered exactly as the miner returns them.
EXPECTED_SAMPLE = [
    (
        "tpl_1tqqwsw",
        "<INSTRUMENT> <SIDE> MARKET\nSL <PRICE>\nTP <PRICE_LIST>",
        4,
        0.875,
        "accept",
        0,
    ),
    (
        "tpl_1wwtun4",
        "<SIDE_EMOJI> <INSTRUMENT>\nENTRY <RANGE>\nSL <PRICE>\nTP <PRICE_LIST>",
        4,
        0.875,
        "accept",
        0,
    ),
    (
        "tpl_1ov73n4",
        "<SIDE> <INSTRUMENT> <RANGE>\nSL <PRICE>\nTP <PRICE>",
        3,
        0.9375,
        "accept",
        0,
    ),
    (
        "tpl_1ypyh3o",
        "<INSTRUMENT> <SIDE> MARKET\nSTOP BELOW <PRICE>\nTARGETS <PRICE_LIST>",
        3,
        0.875,
        "accept",
        0,
    ),
    (
        "tpl_repdqk",
        "<INSTRUMENT> <SIDE>\nSL <PRICE>\nTP <PRICE_LIST>",
        3,
        0.8125,
        "accept",
        0,
    ),
    (
        "tpl_m6w6mu",
        "<INSTRUMENT> <SIDE> ZONE <RANGE>\nINVALIDATION <PRICE>\nTARGETS <PRICE_LIST>",
        2,
        0.9375,
        "accept",
        0,
    ),
    (
        "tpl_s800x0",
        "<INSTRUMENT> <SIDE> @ <PRICE>\nSL <PRICE>\nTP <PRICE>",
        2,
        0.9375,
        "accept",
        0,
    ),
    (
        "tpl_tcanzi",
        "<SIDE> <INSTRUMENT>\nENTRY <RANGE>\nSTOP <PRICE>\nTARGETS <PRICE_LIST>",
        2,
        0.9375,
        "accept",
        0,
    ),
    (
        "tpl_19vbiu9",
        "<INSTRUMENT> <SIDE> ABOVE <PRICE>\nSL <PRICE>\nTP <PRICE>",
        1,
        0.9375,
        "accept",
        0,
    ),
    (
        "tpl_ng9fus",
        "<INSTRUMENT> <SIDE> <PRICE>\nSL <PRICE>\nTP <PRICE>",
        1,
        0.9375,
        "accept",
        0,
    ),
]

EXPECTED_FEED = [
    (
        "tpl_17eas6r",
        "<SIDE> <INSTRUMENT>\nENTRY <PRICE>\nSL <PRICE>\nTP <PRICE_LIST>",
        2,
        0.9375,
        "accept",
        0,
    ),
    (
        "tpl_16p7q70",
        "<SIDE> <INSTRUMENT>\nENTRY <RANGE>\nSTOP <PRICE>\n"
        "TARGETS <PRICE_LIST>\nLEVERAGE <LEVERAGE>",
        1,
        0.9375,
        "accept",
        0,
    ),
    (
        "tpl_1wuiujr",
        "<SIDE> <INSTRUMENT>\nENTRY <RANGE>\nSL <PRICE>\nTP <PRICE_LIST>",
        1,
        0.9375,
        "accept",
        0,
    ),
    (
        "tpl_19eq6rf",
        "<SIDE> <INSTRUMENT> <PRICE>\nSL <PRICE>\nTP <PRICE_LIST>",
        1,
        0.9375,
        "accept",
        0,
    ),
    (
        "tpl_2cbd2o",
        "<*> <INSTRUMENT> <SIDE> <PRICE>\n<*> STOP <PRICE>\nTARGET <PRICE>",
        1,
        0.6875,
        "accept",
        0,
    ),
]


def _summary(group):
    return (
        group.template_key,
        group.normalized_template,
        group.count,
        group.confidence_avg,
        group.suggested_action,
        group.geometry_warnings,
    )


def test_sample_dataset_size_matches_js():
    assert len(SAMPLE_MESSAGES) == 42


def test_feed_dataset_size_matches_js():
    assert len(FEED_MESSAGES) == 18


def test_sample_groups_match_golden():
    groups = mine_template_groups(SAMPLE_MESSAGES)
    assert [_summary(g) for g in groups] == EXPECTED_SAMPLE


def test_feed_groups_match_golden():
    groups = mine_template_groups(FEED_MESSAGES)
    assert [_summary(g) for g in groups] == EXPECTED_FEED


def test_sample_every_family_is_pure_new_signal():
    groups = mine_template_groups(SAMPLE_MESSAGES)
    for group in groups:
        assert group.intent_distribution["new_signal"] == group.count
        assert group.status == "unreviewed"


def test_sample_total_candidates_excludes_noise_updates_results():
    groups = mine_template_groups(SAMPLE_MESSAGES)
    total = sum(group.count for group in groups)
    # 25 signal messages across families A-I; updates/results/commentary/noise drop.
    assert total == 25


def test_sample_ordering_is_count_then_confidence_descending():
    groups = mine_template_groups(SAMPLE_MESSAGES)
    keys = [(g.count, g.confidence_avg) for g in groups]
    assert keys == sorted(keys, key=lambda k: (-k[0], -k[1]))


def test_sample_examples_capped_at_five_and_sorted_by_confidence():
    groups = mine_template_groups(SAMPLE_MESSAGES)
    for group in groups:
        confidences = [c.confidence for c in group.examples]
        assert len(confidences) <= 5
        assert confidences == sorted(confidences, reverse=True)


def test_feed_multi_message_family_carries_expected_instruments():
    groups = mine_template_groups(FEED_MESSAGES)
    biggest = groups[0]
    instruments = [c.fields.instrument for c in biggest.candidates]
    assert instruments == ["ETHUSDT", "LINKUSDT"]


def test_feed_at_least_one_candidate_extracted():
    groups = mine_template_groups(FEED_MESSAGES)
    assert sum(group.count for group in groups) > 0
