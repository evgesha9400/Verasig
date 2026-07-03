"""Wire schemas for Mining Confirm's compiled rules (ADR 0015).

The browser mines templates and compiles them into a `FilterRule` (recall-first
include/exclude patterns) plus ordered `ParserRule`s (patterns + field map +
side aliases). These schemas validate the wire shape before it reaches
persistence; they intentionally omit the `python_*` escape hatches so no dotted
path can arrive from a browser.
"""

import re

from pydantic import field_validator

from verasig.domain.signal import Side
from verasig.foundation.http.schemas import CamelModel

# ExtractedSignal fields a parser rule's named groups may target.
_SIGNAL_FIELDS = {
    "symbol",
    "side",
    "entry",
    "entry_low",
    "entry_high",
    "stop_loss",
    "take_profit",
    "take_profits",
    "leverage",
    "confidence",
}


def _require_compilable(patterns: list[str]) -> list[str]:
    for pattern in patterns:
        try:
            re.compile(pattern)
        except re.error as error:
            # re.error is not a ValueError, so pydantic won't wrap it — do it here
            raise ValueError(f"uncompilable pattern {pattern!r}: {error}") from error
    return patterns


class MinedFilterRuleIn(CamelModel):
    include_patterns: list[str]
    exclude_patterns: list[str] = []
    display: list[dict] = []

    @field_validator("include_patterns")
    @classmethod
    def _at_least_one_include(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("filterRule needs at least one include pattern")
        return _require_compilable(value)

    @field_validator("exclude_patterns")
    @classmethod
    def _excludes_compilable(cls, value: list[str]) -> list[str]:
        return _require_compilable(value)


class MinedParserRuleIn(CamelModel):
    patterns: list[str]
    field_map: dict[str, str] = {}
    side_aliases: dict[str, str] = {}

    @field_validator("patterns")
    @classmethod
    def _at_least_one_compilable(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("parserRule needs at least one pattern")
        return _require_compilable(value)

    @field_validator("field_map")
    @classmethod
    def _targets_are_signal_fields(cls, value: dict[str, str]) -> dict[str, str]:
        unknown = set(value.values()) - _SIGNAL_FIELDS
        if unknown:
            raise ValueError(f"unknown field-map targets: {sorted(unknown)}")
        return value

    @field_validator("side_aliases")
    @classmethod
    def _sides_are_valid(cls, value: dict[str, str]) -> dict[str, str]:
        for side in value.values():
            Side(side)  # raises ValueError -> ValidationError
        return value


class MiningRulesConfirmIn(CamelModel):
    filter_rule: MinedFilterRuleIn
    parser_rules: list[MinedParserRuleIn]

    @field_validator("parser_rules")
    @classmethod
    def _at_least_one_parser(cls, value: list) -> list:
        if not value:
            raise ValueError("confirm needs at least one parser rule")
        return value
