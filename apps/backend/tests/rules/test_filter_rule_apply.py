from verasig.domain.filter_rule import FilterRule
from verasig.features.sources.candidate_filter import apply_filter_rule


def test_include_pattern_match_is_a_candidate():
    rule = FilterRule(rule_id="r", include_patterns=[r"\blong\b"])
    assert apply_filter_rule(rule, "going long here") is True


def test_no_include_match_is_not_a_candidate():
    rule = FilterRule(rule_id="r", include_patterns=[r"\blong\b"])
    assert apply_filter_rule(rule, "gm everyone") is False


def test_include_patterns_are_or_joined():
    rule = FilterRule(rule_id="r", include_patterns=[r"\blong\b", r"\bshort\b"])
    assert apply_filter_rule(rule, "short setup forming") is True


def test_exclude_pattern_carves_out_a_match():
    rule = FilterRule(
        rule_id="r",
        include_patterns=[r"(?i)\bbtc\b"],
        exclude_patterns=[r"(?i)not financial advice"],
    )
    assert apply_filter_rule(rule, "BTC bull run — not financial advice") is False


def test_exclude_does_not_block_when_absent():
    rule = FilterRule(rule_id="r", include_patterns=[r"(?i)\bbtc\b"])
    assert apply_filter_rule(rule, "BTC bull run") is True
