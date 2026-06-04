from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from verasig.domain.filter_rule import FilterRule
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import Side


def test_filter_rule_constructs_with_rule_id_and_include_patterns():
    rule = FilterRule(rule_id="pilot-filter-v1", include_patterns=[r"(?i)\blong\b"])
    assert rule.rule_id == "pilot-filter-v1"
    assert rule.include_patterns == [r"(?i)\blong\b"]


def test_filter_rule_defaults_recall_first_optionals():
    rule = FilterRule(rule_id="pilot-filter-v1", include_patterns=[r"x"])
    assert rule.version == 1
    assert rule.channel_id is None
    assert rule.exclude_patterns == []
    assert rule.recall_target == 0.95
    assert rule.python_filter is None
    assert rule.distilled_from_label_ids == []
    assert isinstance(rule.created_at, datetime)


def test_filter_rule_records_label_provenance():
    label_id = uuid4()
    rule = FilterRule(
        rule_id="r", include_patterns=[r"x"], distilled_from_label_ids=[label_id]
    )
    assert rule.distilled_from_label_ids == [label_id]


def test_filter_rule_rejects_missing_include_patterns():
    with pytest.raises(ValidationError):
        FilterRule(rule_id="r")


def test_parser_rule_constructs_and_coerces_side_aliases_to_side():
    rule = ParserRule(
        rule_id="pilot-parser-v1",
        patterns=[r"(?P<symbol>[A-Z]{2,10})\s+(?P<side>long|short)"],
        field_map={"symbol": "symbol", "side": "side"},
        side_aliases={"long": "LONG", "buy": "LONG", "short": "SHORT"},
    )
    assert rule.side_aliases["long"] is Side.LONG
    assert rule.side_aliases["short"] is Side.SHORT


def test_parser_rule_defaults_optionals():
    rule = ParserRule(rule_id="r", patterns=[r"x"], field_map={})
    assert rule.version == 1
    assert rule.channel_id is None
    assert rule.side_aliases == {}
    assert rule.python_extractor is None
    assert rule.distilled_from_label_ids == []
    assert isinstance(rule.created_at, datetime)


def test_parser_rule_rejects_missing_patterns():
    with pytest.raises(ValidationError):
        ParserRule(rule_id="r", field_map={})
