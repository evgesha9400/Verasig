"""Parity port of ``subsumption.test.js``."""

from verasig.features.rules.template_mining.subsumption import pattern_subsumes


def test_matches_an_identical_skeleton():
    assert pattern_subsumes("BUY <INSTRUMENT>", "BUY <INSTRUMENT>") is True


def test_absorbs_any_single_word_where_the_pattern_has_wildcard():
    assert pattern_subsumes("<*> <INSTRUMENT>", "МОНЕТА <INSTRUMENT>") is True


def test_does_not_match_when_a_literal_word_differs():
    assert pattern_subsumes("BUY <INSTRUMENT>", "SELL <INSTRUMENT>") is False


def test_generalizes_price_list_over_a_single_price():
    assert pattern_subsumes("<INSTRUMENT> <PRICE_LIST>", "<INSTRUMENT> <PRICE>") is True


def test_generalizes_side_over_side_emoji():
    assert pattern_subsumes("<SIDE> <INSTRUMENT>", "<SIDE_EMOJI> <INSTRUMENT>") is True


def test_is_one_directional_specific_pattern_does_not_match_general_message():
    assert (
        pattern_subsumes("<INSTRUMENT> <PRICE>", "<INSTRUMENT> <PRICE_LIST>") is False
    )


def test_keeps_range_and_price_distinct():
    assert pattern_subsumes("<INSTRUMENT> <RANGE>", "<INSTRUMENT> <PRICE>") is False


def test_requires_the_same_number_of_lines():
    assert pattern_subsumes("BUY <INSTRUMENT>", "BUY <INSTRUMENT>\n<PRICE>") is False


def test_requires_the_same_token_count_on_a_line():
    assert pattern_subsumes("<INSTRUMENT>", "<INSTRUMENT> <PRICE>") is False


def test_matches_a_multi_line_skeleton_where_every_line_subsumes():
    assert (
        pattern_subsumes(
            "<*> <INSTRUMENT>\nСТОП <PRICE>\nЦЕЛИ <PRICE_LIST>",
            "МОНЕТА <INSTRUMENT>\nСТОП <PRICE>\nЦЕЛИ <PRICE>",
        )
        is True
    )
