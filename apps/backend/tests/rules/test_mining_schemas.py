"""Wire validation for Mining Confirm's compiled rules (ADR 0015).

The frontend mines templates in the browser and POSTs compiled filter + parser
rules. These schemas reject anything that would poison extraction: uncompilable
regexes, unknown field-map targets, non-LONG/SHORT sides, empty rule sets. The
`python_extractor` / `python_filter` escape hatches are deliberately absent from
the wire shape, so arbitrary dotted paths can never arrive from a browser.
"""

import pytest
from pydantic import ValidationError

from verasig.features.rules.mining_schemas import (
    MinedFilterRuleIn,
    MinedParserRuleIn,
    MiningRulesConfirmIn,
)


def test_valid_confirm_payload_parses_from_camelcase():
    payload = MiningRulesConfirmIn.model_validate(
        {
            "filterRule": {"includePatterns": ["long"], "excludePatterns": []},
            "parserRules": [
                {
                    "patterns": [r"(?P<symbol>\w+)"],
                    "fieldMap": {"symbol": "symbol"},
                    "sideAliases": {"long": "LONG"},
                }
            ],
        }
    )
    assert payload.filter_rule.include_patterns == ["long"]
    assert payload.parser_rules[0].field_map == {"symbol": "symbol"}
    assert payload.parser_rules[0].side_aliases == {"long": "LONG"}


def test_uncompilable_include_pattern_is_rejected():
    with pytest.raises(ValidationError):
        MinedFilterRuleIn.model_validate({"includePatterns": ["(unclosed"]})


def test_empty_include_patterns_rejected():
    with pytest.raises(ValidationError):
        MinedFilterRuleIn.model_validate({"includePatterns": []})


def test_unknown_field_map_target_is_rejected():
    with pytest.raises(ValidationError):
        MinedParserRuleIn.model_validate(
            {"patterns": ["x"], "fieldMap": {"g": "not_a_signal_field"}}
        )


def test_invalid_side_alias_is_rejected():
    with pytest.raises(ValidationError):
        MinedParserRuleIn.model_validate(
            {"patterns": ["x"], "fieldMap": {}, "sideAliases": {"l": "UPWARD"}}
        )


def test_empty_parser_rules_rejected():
    with pytest.raises(ValidationError):
        MiningRulesConfirmIn.model_validate(
            {"filterRule": {"includePatterns": ["x"]}, "parserRules": []}
        )


def test_python_escape_hatch_is_not_accepted_from_wire():
    rule = MinedParserRuleIn.model_validate(
        {"patterns": ["x"], "fieldMap": {}, "pythonExtractor": "evil.module:run"}
    )
    assert not hasattr(rule, "python_extractor")
