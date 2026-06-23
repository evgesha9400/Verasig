import json
from pathlib import Path
from uuid import uuid4

import pytest
from fakes import FakeDistiller

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import DistillationExample, LabelKind
from verasig.domain.llm_ports import RuleDistiller
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import ExtractedSignal, Side
from verasig.features.rules.rule_distiller import (
    AnthropicDistiller,
    FilterDistillationError,
    ParserDistillationError,
    evaluate_filter_candidate,
    evaluate_parser_candidate,
    parse_distiller_output,
    parse_filter_distiller_output,
    parse_parser_distiller_output,
)

FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "cli" / "distill_pilot.txt"
).read_text(encoding="utf-8")


def _labels() -> list[DistillationExample]:
    return [
        DistillationExample(
            channel_id=7,
            message_id=1,
            label=LabelKind.SIGNAL,
            text="BTC long entry 100 stop 90",
        ),
        DistillationExample(
            channel_id=7,
            message_id=2,
            label=LabelKind.NOISE,
            text="Market commentary only",
        ),
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


def test_parse_filter_distiller_output_accepts_include_patterns_only():
    payload = json.dumps({"include_patterns": ["alpha"]})

    filter_rule = parse_filter_distiller_output(payload, channel_id=7, label_ids=[])

    assert filter_rule.include_patterns == ["alpha"]
    assert filter_rule.exclude_patterns == []
    assert filter_rule.display == []


@pytest.mark.parametrize(
    "payload",
    [
        {"filter_rule": {"include_patterns": ["alpha"]}},
        {"include_patterns": ["alpha"], "parser_rules": []},
        {"include_patterns": ["alpha"], "display": []},
        {"include_patterns": ["alpha"], "exclude_patterns": []},
    ],
)
def test_parse_filter_distiller_output_rejects_combined_schema_noise(payload):
    with pytest.raises(ValueError, match="include_patterns"):
        parse_filter_distiller_output(json.dumps(payload), channel_id=7, label_ids=[])


def test_parse_parser_distiller_output_accepts_parser_only_payload():
    payload = json.dumps(
        {
            "parser_rules": [
                {
                    "patterns": ["(?P<symbol>BTC)"],
                    "field_map": {"symbol": "symbol"},
                    "side_aliases": {},
                }
            ]
        }
    )

    parser_rules = parse_parser_distiller_output(payload, channel_id=7, label_ids=[])

    assert parser_rules[0].patterns == ["(?P<symbol>BTC)"]
    assert parser_rules[0].field_map == {"symbol": "symbol"}


def test_evaluate_filter_candidate_reports_perfect_accuracy():
    report = evaluate_filter_candidate([r"(?i)\blong\b"], _labels())

    assert report["accuracy"] == 100.0
    assert report["false_positive_message_ids"] == []
    assert report["false_negative_message_ids"] == []


def test_evaluate_filter_candidate_reports_false_positives_and_false_negatives():
    examples = [
        DistillationExample(
            channel_id=7,
            message_id=1,
            label=LabelKind.SIGNAL,
            text="BTC long entry",
        ),
        DistillationExample(
            channel_id=7,
            message_id=2,
            label=LabelKind.SIGNAL,
            text="ETH short entry",
        ),
        DistillationExample(
            channel_id=7,
            message_id=3,
            label=LabelKind.NOISE,
            text="BTC market commentary",
        ),
    ]

    report = evaluate_filter_candidate([r"(?i)\bbtc\b"], examples)

    assert report["accuracy"] == pytest.approx(33.33, abs=0.01)
    assert report["false_positive_message_ids"] == [3]
    assert report["false_negative_message_ids"] == [2]
    assert (
        report["false_positive_examples"][0]["text_preview"] == "BTC market commentary"
    )
    assert report["false_negative_examples"][0]["text_preview"] == "ETH short entry"


def test_anthropic_distiller_satisfies_protocol():
    assert isinstance(AnthropicDistiller(runner=lambda _prompt: FIXTURE), RuleDistiller)


def test_anthropic_distiller_stops_filter_retry_on_perfect_first_candidate():
    prompts: list[str] = []

    def fake_runner(prompt: str) -> str:
        prompts.append(prompt)
        return json.dumps({"include_patterns": [r"(?i)\blong\b"]})

    distiller = AnthropicDistiller(runner=fake_runner)
    filter_rule = distiller.distill_filter(_labels())

    assert isinstance(filter_rule, FilterRule) and filter_rule.channel_id == 7
    assert filter_rule.include_patterns == [r"(?i)\blong\b"]
    assert len(prompts) == 1


def test_anthropic_distiller_widens_decorative_literal_prefixes_when_still_perfect():
    examples = [
        DistillationExample(
            channel_id=7,
            message_id=1,
            label=LabelKind.SIGNAL,
            text="⚫️ Вход: BTC",
        ),
        DistillationExample(
            channel_id=7,
            message_id=2,
            label=LabelKind.SIGNAL,
            text="1️⃣ТЕЙК hit",
        ),
        DistillationExample(
            channel_id=7,
            message_id=3,
            label=LabelKind.NOISE,
            text="Market commentary",
        ),
    ]

    distiller = AnthropicDistiller(
        runner=lambda _prompt: json.dumps({"include_patterns": ["⚫️ Вход:", "️⃣ТЕЙК"]})
    )

    filter_rule = distiller.distill_filter(examples)

    assert filter_rule.include_patterns == ["Вход:", "ТЕЙК"]


def test_anthropic_distiller_keeps_decorative_prefix_when_widening_is_not_perfect():
    examples = [
        DistillationExample(
            channel_id=7,
            message_id=1,
            label=LabelKind.SIGNAL,
            text="⚫️ Вход: BTC",
        ),
        DistillationExample(
            channel_id=7,
            message_id=2,
            label=LabelKind.NOISE,
            text="Вход: newsletter section",
        ),
    ]

    distiller = AnthropicDistiller(
        runner=lambda _prompt: json.dumps({"include_patterns": ["⚫️ Вход:"]})
    )

    filter_rule = distiller.distill_filter(examples)

    assert filter_rule.include_patterns == ["⚫️ Вход:"]


def test_anthropic_distiller_retries_filter_with_validation_feedback():
    prompts: list[str] = []

    def fake_runner(prompt: str) -> str:
        prompts.append(prompt)
        if len(prompts) == 1:
            return json.dumps({"include_patterns": [r"(?i)\bmarket\b"]})
        return json.dumps({"include_patterns": [r"(?i)\blong\b"]})

    distiller = AnthropicDistiller(runner=fake_runner)
    filter_rule = distiller.distill_filter(_labels())

    assert filter_rule.include_patterns == [r"(?i)\blong\b"]
    assert len(prompts) == 2
    assert "Previous include_patterns" in prompts[1]
    assert "false positives" in prompts[1]
    assert "false negatives" in prompts[1]
    assert "BTC long entry 100 stop 90" in prompts[1]
    assert "Market commentary only" in prompts[1]


def test_anthropic_distiller_truncates_long_filter_prompt_examples():
    prompts: list[str] = []
    long_tail = "tail-token " * 200
    examples = [
        DistillationExample(
            channel_id=7,
            message_id=1,
            label=LabelKind.SIGNAL,
            text=f"SIGNAL_HEAD {long_tail}",
        ),
        DistillationExample(
            channel_id=7,
            message_id=2,
            label=LabelKind.NOISE,
            text=f"NOISE_HEAD {long_tail}",
        ),
    ]

    def fake_runner(prompt: str) -> str:
        prompts.append(prompt)
        return json.dumps({"include_patterns": ["SIGNAL_HEAD"]})

    AnthropicDistiller(runner=fake_runner).distill_filter(examples)

    assert "SIGNAL_HEAD" in prompts[0]
    assert "NOISE_HEAD" in prompts[0]
    assert prompts[0].count("tail-token") < 120
    assert "..." in prompts[0]


def test_anthropic_distiller_fails_after_three_invalid_filter_candidates():
    calls = 0

    def fake_runner(_prompt: str) -> str:
        nonlocal calls
        calls += 1
        return json.dumps({"include_patterns": [r"(?i)\bmarket\b"]})

    distiller = AnthropicDistiller(runner=fake_runner)

    with pytest.raises(FilterDistillationError) as error:
        distiller.distill_filter(_labels())

    assert calls == 3
    assert error.value.report["accuracy"] < 100.0


def test_anthropic_distiller_distills_parser_without_expected_fields():
    prompts: list[str] = []

    distiller = AnthropicDistiller(
        runner=lambda prompt: (
            prompts.append(prompt)
            or json.dumps(
                {
                    "parser_rules": [
                        {
                            "patterns": [r"(?P<symbol>BTC)\s+(?P<side>long)"],
                            "field_map": {"symbol": "symbol", "side": "side"},
                            "side_aliases": {"long": "LONG"},
                        }
                    ]
                }
            )
        ),
    )

    rules = distiller.distill_parsers(_labels())

    assert len(rules) == 1
    assert len(prompts) == 1
    assert "message 1: label=signal" in prompts[0]
    assert "message 2: label=noise" in prompts[0]
    assert "symbol and side are compulsory" in prompts[0]
    assert "multiple take profits" in prompts[0]
    assert "entry_low and entry_high" in prompts[0]
    assert "no entry is present" in prompts[0]


def test_parser_validation_ignores_signal_updates_without_symbol_and_side():
    examples = [
        DistillationExample(
            channel_id=7,
            message_id=1,
            label=LabelKind.SIGNAL,
            text="Монета: BTC\nКупил в Лонг\nВход: $100\nСтоп: $90",
        ),
        DistillationExample(
            channel_id=7,
            message_id=2,
            label=LabelKind.SIGNAL,
            text="1️⃣ Тейк пробили!! фиксируем часть и ставим стоп в бу",
        ),
    ]
    rule = ParserRule(
        rule_id="r1",
        channel_id=7,
        patterns=[
            r"Монет[ау]?:\s*(?P<symbol>[A-Z]{2,10}).*?"
            r"Купил\s+в\s+(?P<side>Лонг|Шорт)"
        ],
        field_map={"symbol": "symbol", "side": "side"},
        side_aliases={"лонг": "LONG", "шорт": "SHORT"},
    )

    report = evaluate_parser_candidate([rule], examples)

    assert report["parser_required_signal_count"] == 1
    assert report["parser_excluded_signal_message_ids"] == [2]
    assert report["missing_signal_message_ids"] == []


def test_anthropic_distiller_does_not_prompt_signal_updates_without_required_clues():
    prompts: list[str] = []
    examples = [
        DistillationExample(
            channel_id=7,
            message_id=1,
            label=LabelKind.SIGNAL,
            text="Монета: BTC\nКупил в Лонг\nВход: $100\nСтоп: $90",
        ),
        DistillationExample(
            channel_id=7,
            message_id=2,
            label=LabelKind.SIGNAL,
            text="1️⃣ Тейк пробили!! фиксируем часть и ставим стоп в бу",
        ),
        DistillationExample(
            channel_id=7,
            message_id=3,
            label=LabelKind.NOISE,
            text="Market commentary",
        ),
    ]

    def fake_runner(prompt: str) -> str:
        prompts.append(prompt)
        return json.dumps(
            {
                "parser_rules": [
                    {
                        "patterns": [
                            r"Монет[ау]?:\s*(?P<symbol>[A-Z]{2,10}).*?"
                            r"Купил\s+в\s+(?P<side>Лонг|Шорт)"
                        ],
                        "field_map": {"symbol": "symbol", "side": "side"},
                        "side_aliases": {"лонг": "LONG", "шорт": "SHORT"},
                    }
                ]
            }
        )

    rules = AnthropicDistiller(runner=fake_runner).distill_parsers(examples)

    assert len(rules) == 1
    assert "message 1" in prompts[0]
    assert "message 2" not in prompts[0]
    assert "message 3" in prompts[0]


def test_anthropic_distiller_skips_parser_when_no_signal_labels_exist():
    prompts: list[str] = []
    skips: list[str] = []
    examples = [
        DistillationExample(
            channel_id=7,
            message_id=12,
            label=LabelKind.NOISE,
            text="Market commentary",
        )
    ]
    distiller = AnthropicDistiller(
        runner=lambda prompt: (
            prompts.append(prompt) or json.dumps({"parser_rules": []})
        ),
        parser_skip_auditor=lambda _kind, content, _examples: skips.append(content),
    )

    assert distiller.distill_parsers(examples) == []
    assert prompts == []
    assert skips == [
        "parser distillation skipped because parser_required_signal_count=0"
    ]


def test_anthropic_distiller_sends_all_labeled_examples_to_parser():
    signal_expected = DistillationExample(
        channel_id=7,
        message_id=10,
        label=LabelKind.SIGNAL,
        text="BTC long entry",
        expected=ExtractedSignal(
            event_id=uuid4(),
            channel_id=7,
            symbol="BTC",
            side=Side.LONG,
        ),
    )
    signal_without_expected = DistillationExample(
        channel_id=7,
        message_id=11,
        label=LabelKind.SIGNAL,
        text="ETH long entry",
    )
    noise = DistillationExample(
        channel_id=7,
        message_id=12,
        label=LabelKind.NOISE,
        text="Market commentary",
    )
    prompts: list[str] = []

    def fake_runner(prompt: str) -> str:
        prompts.append(prompt)
        return json.dumps(
            {
                "parser_rules": [
                    {
                        "patterns": [r"(?P<symbol>BTC|ETH)\s+(?P<side>long)"],
                        "field_map": {"symbol": "symbol", "side": "side"},
                        "side_aliases": {"long": "LONG"},
                    }
                ]
            }
        )

    distiller = AnthropicDistiller(runner=fake_runner)

    rules = distiller.distill_parsers([signal_expected, signal_without_expected, noise])

    assert len(rules) == 1
    assert "message 10" in prompts[0]
    assert "message 11" in prompts[0]
    assert "message 12" in prompts[0]
    assert '"symbol":"BTCUSDT"' in prompts[0]
    assert '"filter_rule"' not in prompts[0]


def test_anthropic_distiller_retries_parser_with_deterministic_feedback():
    prompts: list[str] = []
    responses = [
        json.dumps(
            {
                "parser_rules": [
                    {
                        "patterns": [r"(?P<symbol>BTC)"],
                        "field_map": {"symbol": "symbol"},
                        "side_aliases": {},
                    }
                ]
            }
        ),
        json.dumps(
            {
                "parser_rules": [
                    {
                        "patterns": [r"(?P<symbol>BTC)\s+(?P<side>long)"],
                        "field_map": {"symbol": "symbol", "side": "side"},
                        "side_aliases": {"long": "LONG"},
                    }
                ]
            }
        ),
    ]

    def fake_runner(prompt: str) -> str:
        prompts.append(prompt)
        return responses.pop(0)

    distiller = AnthropicDistiller(runner=fake_runner)
    rules = distiller.distill_parsers(_labels())

    assert len(rules) == 1
    assert len(prompts) == 2
    assert "Previous parser candidate failed deterministic validation" in prompts[1]
    assert "missing_signal_message_ids" in prompts[1]
    assert "BTC long entry 100 stop 90" in prompts[1]


def test_anthropic_distiller_fails_after_three_invalid_parser_candidates():
    calls = 0

    def fake_runner(_prompt: str) -> str:
        nonlocal calls
        calls += 1
        return json.dumps(
            {
                "parser_rules": [
                    {
                        "patterns": [r"(?P<symbol>BTC)"],
                        "field_map": {"symbol": "symbol"},
                        "side_aliases": {},
                    }
                ]
            }
        )

    distiller = AnthropicDistiller(runner=fake_runner)

    with pytest.raises(ParserDistillationError) as error:
        distiller.distill_parsers(_labels())

    assert calls == 3
    assert error.value.report["missing_signal_message_ids"] == [1]


def test_fake_distiller_returns_rules_from_canned_output():
    distiller = FakeDistiller(FIXTURE)
    assert isinstance(distiller, RuleDistiller)
    assert isinstance(distiller.distill_filter(_labels()), FilterRule)
    assert distiller.distill_parsers(_labels())
