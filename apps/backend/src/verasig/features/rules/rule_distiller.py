"""Human-assisted rule distillation (data-contracts.md §9; ADR 0005).

One `GoldenLabel` pass yields a recall-first `FilterRule` (from `label`) and
precision-first `ParserRule`s (from `expected`). The LLM emits JSON carrying ONLY
pattern content; `parse_distiller_output` tolerantly extracts it (bare or
```json-fenced), validates via Pydantic, and the adapter stamps provenance
(`rule_id`/`version`/`distilled_from_label_ids`) — never trusting the model for it.
Only operator-selected examples reach the model (privacy, spec §10); no test ever
invokes the real CLI (the subprocess runner is injectable).
"""

import json
from collections.abc import Callable
from uuid import UUID

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel
from verasig.domain.llm_ports import RuleDistiller
from verasig.domain.parser_rule import ParserRule
from verasig.shared.json_object import find_json_object

_FILTER_KEYS = {
    "include_patterns",
    "exclude_patterns",
    "matched_reason_template",
    "recall_target",
    "display",
}
_PARSER_KEYS = {"patterns", "field_map", "side_aliases"}


def _extract_json(stdout: str) -> dict:
    raw = find_json_object(stdout)
    if raw is None:
        raise ValueError("no JSON object in distiller output")
    return json.loads(raw)


def _content(payload: dict, allowed: set[str]) -> dict:
    # keep only declarative pattern content; provenance is adapter-stamped
    return {key: value for key, value in payload.items() if key in allowed}


def parse_distiller_output(
    stdout: str,
    *,
    channel_id: int,
    label_ids: list,
    version: int = 1,
    user_id: UUID | None = None,
) -> tuple[FilterRule, list[ParserRule]]:
    data = _extract_json(stdout)
    filter_rule_id = (
        f"{user_id}:{channel_id}-filter-v{version}"
        if user_id is not None
        else f"{channel_id}-filter-v{version}"
    )
    filter_rule = FilterRule(
        rule_id=filter_rule_id,
        user_id=user_id,
        channel_id=channel_id,
        version=version,
        distilled_from_label_ids=label_ids,
        **_content(data.get("filter_rule", {}), _FILTER_KEYS),
    )
    parser_rules = [
        ParserRule(
            rule_id=(
                f"{user_id}:{channel_id}-parser-{index + 1}-v{version}"
                if user_id is not None
                else f"{channel_id}-parser-{index + 1}-v{version}"
            ),
            user_id=user_id,
            channel_id=channel_id,
            version=version,
            distilled_from_label_ids=label_ids,
            **_content(payload, _PARSER_KEYS),
        )
        for index, payload in enumerate(data.get("parser_rules", []))
    ]
    return filter_rule, parser_rules


def _label_lines(labels: list[GoldenLabel]) -> str:
    lines = []
    for label in labels:
        line = f"- message {label.message_id}: label={label.label.value}"
        if label.expected is not None:
            line += f" expected={label.expected.model_dump_json(exclude_none=True)}"
        lines.append(line)
    return "\n".join(lines)


def _filter_prompt(labels: list[GoldenLabel]) -> str:
    return (
        "Distil a RECALL-FIRST FilterRule: loose, OR-joined include_patterns that "
        "flag every label=signal example (false positives are acceptable). "
        'Return JSON {"filter_rule": {"include_patterns": [...], '
        '"exclude_patterns": [...], "matched_reason_template": "...", '
        '"recall_target": 0.95, "display": [{"label": "...", "detail": "..."}]}, '
        '"parser_rules": []}.\n\n'
        f"Labeled examples:\n{_label_lines(labels)}"
    )


def _parser_prompt(labels: list[GoldenLabel]) -> str:
    return (
        "Distil PRECISION-FIRST ParserRules: ordered regexes whose named groups map "
        "via field_map onto ExtractedSignal fields, reproducing the expected fields. "
        'Return JSON {"filter_rule": {"include_patterns": []}, "parser_rules": '
        '[{"patterns": [...], "field_map": {...}, "side_aliases": {...}}]}.\n\n'
        f"Labeled examples:\n{_label_lines(labels)}"
    )


class AnthropicDistiller(RuleDistiller):
    """Anthropic-backed rule distiller over an injected prompt runner."""

    def __init__(self, runner: Callable[[str], str], version: int = 1) -> None:
        self._runner = runner
        self._version = version

    def distill_filter(self, labels: list[GoldenLabel]) -> FilterRule:
        return self._distill(labels, _filter_prompt(labels))[0]

    def distill_parsers(self, labels: list[GoldenLabel]) -> list[ParserRule]:
        return self._distill(labels, _parser_prompt(labels))[1]

    def _distill(
        self, labels: list[GoldenLabel], prompt: str
    ) -> tuple[FilterRule, list[ParserRule]]:
        if not labels:
            raise ValueError("no labels to distill")
        stdout = self._runner(prompt)
        return parse_distiller_output(
            stdout,
            channel_id=labels[0].channel_id,
            label_ids=[label.id for label in labels],
            version=self._version,
        )
