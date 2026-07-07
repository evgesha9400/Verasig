"""Parity port of ``specificity.test.js``."""

from verasig.features.mining.template_mining.specificity import template_specificity


def test_scores_a_literal_placeholder_template_above_a_sparser_one():
    assert template_specificity("МОНЕТА <INSTRUMENT> <SIDE>") > template_specificity(
        "<INSTRUMENT> <SIDE>"
    )


def test_penalises_a_wildcard_below_a_literal_structural_word():
    assert template_specificity("МОНЕТА <INSTRUMENT>") > template_specificity(
        "<*> <INSTRUMENT>"
    )


def test_counts_value_placeholders_as_structure():
    assert template_specificity("<INSTRUMENT> <PRICE> <SIDE>") > template_specificity(
        "<INSTRUMENT>"
    )


def test_sums_structure_across_multiple_lines():
    assert template_specificity("BUY <INSTRUMENT>\nSL <PRICE>") > template_specificity(
        "BUY <INSTRUMENT>"
    )


def test_returns_0_for_an_empty_or_missing_template():
    assert template_specificity("") == 0
    assert template_specificity(None) == 0
