import json
from pathlib import Path
from uuid import uuid4

from fakes import FakeDistiller

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel, LabelKind
from verasig.domain.llm_ports import RuleDistiller
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import Side
from verasig.features.rules.rule_distiller import (
    AnthropicDistiller,
    parse_distiller_output,
)

FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "cli" / "distill_pilot.txt"
).read_text(encoding="utf-8")


def _labels() -> list[GoldenLabel]:
    return [
        GoldenLabel(channel_id=7, message_id=1, label=LabelKind.SIGNAL),
        GoldenLabel(channel_id=7, message_id=2, label=LabelKind.NOISE),
    ]


def test_parse_distiller_output_builds_validated_rules_with_provenance():
    label_ids = [uuid4(), uuid4()]
    filter_rule, parser_rules = parse_distiller_output(
        FIXTURE, channel_id=7, label_ids=label_ids
    )
    assert isinstance(filter_rule, FilterRule)
    assert filter_rule.channel_id == 7
    assert filter_rule.rule_id == "7-filter-v1"
    assert filter_rule.distilled_from_label_ids == label_ids
    assert filter_rule.include_patterns
    assert all(isinstance(rule, ParserRule) for rule in parser_rules)
    assert parser_rules[0].side_aliases["long"] is Side.LONG
    assert parser_rules[0].rule_id == "7-parser-1-v1"


def test_parse_distiller_output_tolerates_bare_json():
    bare = json.dumps({"filter_rule": {"include_patterns": ["x"]}, "parser_rules": []})
    filter_rule, parser_rules = parse_distiller_output(bare, channel_id=1, label_ids=[])
    assert filter_rule.include_patterns == ["x"]
    assert parser_rules == []


def test_parse_distiller_output_ignores_hallucinated_provenance_keys():
    sneaky = json.dumps(
        {
            "filter_rule": {
                "include_patterns": ["x"],
                "rule_id": "HACKED",
                "distilled_from_label_ids": ["nope"],
            },
            "parser_rules": [],
        }
    )
    filter_rule, _ = parse_distiller_output(sneaky, channel_id=9, label_ids=[])
    assert filter_rule.rule_id == "9-filter-v1"  # adapter-stamped, not hallucinated
    assert filter_rule.distilled_from_label_ids == []


def test_parse_distiller_output_stamps_version_into_rule_ids():
    bare = '{"filter_rule":{"include_patterns":["x"]},"parser_rules":[]}'
    filter_rule, _ = parse_distiller_output(bare, channel_id=7, label_ids=[], version=3)
    assert filter_rule.rule_id == "7-filter-v3"
    assert filter_rule.version == 3


def test_parse_distiller_output_stamps_user_scope_and_display():
    user_id = uuid4()
    payload = json.dumps(
        {
            "filter_rule": {
                "include_patterns": ["alpha"],
                "display": [{"label": "Alpha", "detail": "Mentions alpha"}],
            },
            "parser_rules": [{"patterns": ["x"], "field_map": {}, "side_aliases": {}}],
        }
    )

    filter_rule, parser_rules = parse_distiller_output(
        payload, channel_id=7, label_ids=[], user_id=user_id
    )

    assert filter_rule.user_id == user_id
    assert filter_rule.rule_id == f"{user_id}:7-filter-v1"
    assert filter_rule.display == [{"label": "Alpha", "detail": "Mentions alpha"}]
    assert parser_rules[0].rule_id == f"{user_id}:7-parser-1-v1"


def test_anthropic_distiller_satisfies_protocol():
    assert isinstance(AnthropicDistiller(runner=lambda _prompt: FIXTURE), RuleDistiller)


def test_anthropic_distiller_wires_runner_to_parser_without_real_network():
    prompts: list[str] = []

    def fake_runner(prompt: str) -> str:
        prompts.append(prompt)
        return FIXTURE

    distiller = AnthropicDistiller(runner=fake_runner)
    filter_rule = distiller.distill_filter(_labels())
    parser_rules = distiller.distill_parsers(_labels())
    assert isinstance(filter_rule, FilterRule) and filter_rule.channel_id == 7
    assert parser_rules and isinstance(parser_rules[0], ParserRule)
    assert len(prompts) == 2  # one recall-first, one precision-first; no real CLI


def test_fake_distiller_returns_rules_from_canned_output():
    distiller = FakeDistiller(FIXTURE)
    assert isinstance(distiller, RuleDistiller)
    assert isinstance(distiller.distill_filter(_labels()), FilterRule)
    assert distiller.distill_parsers(_labels())
