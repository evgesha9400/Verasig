"""Human-assisted rule distillation (data-contracts.md §9; ADR 0005).

Claude proposes include-only filter candidates and parser-rule candidates. Backend
code validates every candidate against the hydrated labelled examples, retries
with deterministic feedback, and persists only candidates that pass the available
oracle. Parser distillation uses signal labels even when structured `expected`
fields are not yet present; expected fields tighten validation when available.
The adapter stamps provenance
(`rule_id`/`version`/`distilled_from_label_ids`), never trusting the model for it.
Only operator-selected examples reach the model (privacy, spec §10); no test ever
invokes the real CLI (the subprocess runner is injectable).
"""

import json
import re
import unicodedata
from collections.abc import Callable
from uuid import UUID

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import DistillationExample, LabelKind
from verasig.domain.llm_ports import RuleDistiller
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import TradeIntent
from verasig.features.signals.deterministic_parser import parse
from verasig.shared.json_object import find_json_object

_FILTER_MAX_ATTEMPTS = 3
_PARSER_MAX_ATTEMPTS = 3
_FILTER_CONTRACT_KEYS = {"include_patterns"}
_INLINE_FLAG_PATTERN = re.compile(r"^(\(\?[aiLmsux-]+\))")
_KEYCAP_PREFIX_PATTERN = re.compile(r"^([0-9#*]\ufe0f?\u20e3)+")
_REGEX_META_CHARS = frozenset("\\^$.*+?{}[]|()")
_PARSER_SYMBOL_CLUE_PATTERN = re.compile(
    r"(?:монет[ау]?\s*:)|(?:[#\$]?[A-Z0-9]{2,12}(?:/USDT|USDT)?\b)",
    re.IGNORECASE,
)
_PARSER_SIDE_CLUE_PATTERN = re.compile(
    r"\b(?:long|short|buy|sell|лонг|шорт)\b",
    re.IGNORECASE,
)
_PARSER_GUARD_CLUE_PATTERN = re.compile(
    r"(?:entry|stop|target|long|short|signal|coin|вход|стоп|цел[ьи]|тейк|"
    r"лонг|шорт|монет|сделк)",
    re.IGNORECASE,
)
_PARSER_GUARD_EXAMPLE_LIMIT = 12
_PARSER_SIGNAL_TEXT_LIMIT = 1200
_PARSER_GUARD_TEXT_LIMIT = 500
_FILTER_KEYS = {
    "include_patterns",
    "exclude_patterns",
    "matched_reason_template",
    "recall_target",
    "display",
}
_PARSER_KEYS = {"patterns", "field_map", "side_aliases"}
PromptAuditor = Callable[[str, str, list[DistillationExample]], None]
ValidationAuditor = Callable[[str, dict, list[DistillationExample]], None]


class FilterDistillationError(Exception):
    def __init__(self, report: dict) -> None:
        super().__init__("filter distillation failed deterministic validation")
        self.report = report


class ParserDistillationError(Exception):
    def __init__(self, report: dict) -> None:
        super().__init__("parser distillation failed deterministic validation")
        self.report = report


def _extract_json(stdout: str) -> dict:
    raw = find_json_object(stdout)
    if raw is None:
        raise ValueError("no JSON object in distiller output")
    return json.loads(raw)


def _content(payload: dict, allowed: set[str]) -> dict:
    # keep only declarative pattern content; provenance is adapter-stamped
    return {key: value for key, value in payload.items() if key in allowed}


def _require_filter_contract(data: object) -> list[str]:
    if not isinstance(data, dict):
        raise ValueError(
            'filter output must be JSON object {"include_patterns": [...]}'
        )
    if set(data) != _FILTER_CONTRACT_KEYS:
        raise ValueError('filter output must contain only "include_patterns"')
    include_patterns = data["include_patterns"]
    if not isinstance(include_patterns, list):
        raise ValueError('"include_patterns" must be a list of regex strings')
    if not all(isinstance(pattern, str) for pattern in include_patterns):
        raise ValueError('"include_patterns" must be a list of regex strings')
    return include_patterns


def _require_parser_contract(data: object) -> list[dict]:
    if not isinstance(data, dict):
        raise ValueError('parser output must be JSON object {"parser_rules": [...]}')
    if set(data) != {"parser_rules"}:
        raise ValueError('parser output must contain only "parser_rules"')
    parser_rules = data["parser_rules"]
    if not isinstance(parser_rules, list):
        raise ValueError('"parser_rules" must be a list')
    if not all(isinstance(rule, dict) for rule in parser_rules):
        raise ValueError('"parser_rules" must be a list of objects')
    return parser_rules


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


def parse_filter_distiller_output(
    stdout: str,
    *,
    channel_id: int,
    label_ids: list,
    version: int = 1,
    user_id: UUID | None = None,
) -> FilterRule:
    data = _extract_json(stdout)
    include_patterns = _require_filter_contract(data)
    rule_id = (
        f"{user_id}:{channel_id}-filter-v{version}"
        if user_id is not None
        else f"{channel_id}-filter-v{version}"
    )
    return FilterRule(
        rule_id=rule_id,
        user_id=user_id,
        channel_id=channel_id,
        version=version,
        distilled_from_label_ids=label_ids,
        include_patterns=include_patterns,
        exclude_patterns=[],
    )


def parse_parser_distiller_output(
    stdout: str,
    *,
    channel_id: int,
    label_ids: list,
    version: int = 1,
    user_id: UUID | None = None,
) -> list[ParserRule]:
    data = _extract_json(stdout)
    parser_payloads = _require_parser_contract(data)
    return [
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
        for index, payload in enumerate(parser_payloads)
    ]


def evaluate_filter_candidate(
    include_patterns: list[str], examples: list[DistillationExample]
) -> dict:
    compiled_patterns, regex_errors = _compile_include_patterns(include_patterns)
    false_positive_examples = []
    false_negative_examples = []
    for example in examples:
        predicted_signal = _matches_any(compiled_patterns, example.text or "")
        if predicted_signal and not example.is_signal:
            false_positive_examples.append(example)
        if not predicted_signal and example.is_signal:
            false_negative_examples.append(example)
    correct_count = (
        len(examples) - len(false_positive_examples) - len(false_negative_examples)
    )
    accuracy = round((correct_count / len(examples)) * 100, 2) if examples else 0.0
    return {
        "include_patterns": include_patterns,
        "total_labelled_examples": len(examples),
        "signal_count": _count(examples, LabelKind.SIGNAL),
        "noise_count": _count(examples, LabelKind.NOISE),
        "modifier_count": _count(examples, LabelKind.MODIFIER),
        "accuracy": accuracy,
        "correct_count": correct_count,
        "false_positive_message_ids": [
            example.message_id for example in false_positive_examples
        ],
        "false_negative_message_ids": [
            example.message_id for example in false_negative_examples
        ],
        "false_positive_examples": [
            _validation_example(example) for example in false_positive_examples
        ],
        "false_negative_examples": [
            _validation_example(example) for example in false_negative_examples
        ],
        "regex_errors": regex_errors,
    }


def _compile_include_patterns(
    include_patterns: list[str],
) -> tuple[list[re.Pattern], list[dict]]:
    compiled_patterns = []
    regex_errors = []
    for pattern in include_patterns:
        try:
            compiled_patterns.append(re.compile(pattern))
        except re.error as error:
            regex_errors.append({"pattern": pattern, "error": str(error)})
    return compiled_patterns, regex_errors


def _matches_any(compiled_patterns: list[re.Pattern], text: str) -> bool:
    return any(pattern.search(text) is not None for pattern in compiled_patterns)


def _validation_example(example: DistillationExample) -> dict:
    text = example.text or ""
    return {
        "message_id": example.message_id,
        "label": example.label.value,
        "text_preview": text[:240],
    }


def _count(examples: list[DistillationExample], label: LabelKind) -> int:
    return sum(1 for example in examples if example.label == label)


def _invalid_filter_candidate_report(
    error: Exception, examples: list[DistillationExample]
) -> dict:
    report = evaluate_filter_candidate([], examples)
    report["candidate_error"] = str(error)
    return report


def _filter_candidate_is_perfect(report: dict) -> bool:
    if report.get("candidate_error"):
        return False
    if report.get("regex_errors"):
        return False
    return report["accuracy"] == 100.0


def evaluate_parser_candidate(
    parser_rules: list[ParserRule], examples: list[DistillationExample]
) -> dict:
    regex_errors = _compile_parser_patterns(parser_rules)
    predictions = {} if regex_errors else _parse_predictions(examples, parser_rules)
    required_signal_examples = _parser_required_signal_examples(examples)
    excluded_signal_examples = _parser_excluded_signal_examples(examples)
    missing_signal_examples = _missing_signal_examples(
        required_signal_examples, predictions
    )
    false_positive_examples = _false_positive_examples(examples, predictions)
    expected_mismatch_examples = _expected_mismatch_examples(examples, predictions)
    correct_count = (
        len(examples)
        - len(missing_signal_examples)
        - len(false_positive_examples)
        - len(expected_mismatch_examples)
    )
    accuracy = round((correct_count / len(examples)) * 100, 2) if examples else 0.0
    return {
        "parser_rule_count": len(parser_rules),
        "total_labelled_examples": len(examples),
        "signal_count": _count(examples, LabelKind.SIGNAL),
        "parser_required_signal_count": len(required_signal_examples),
        "parser_excluded_signal_count": len(excluded_signal_examples),
        "noise_count": _count(examples, LabelKind.NOISE),
        "modifier_count": _count(examples, LabelKind.MODIFIER),
        "extracted_count": len(predictions),
        "accuracy": accuracy,
        "correct_count": correct_count,
        "missing_signal_message_ids": [
            example.message_id for example in missing_signal_examples
        ],
        "false_positive_message_ids": [
            example.message_id for example in false_positive_examples
        ],
        "expected_mismatch_message_ids": [
            item["message_id"] for item in expected_mismatch_examples
        ],
        "parser_excluded_signal_message_ids": [
            example.message_id for example in excluded_signal_examples
        ],
        "missing_signal_examples": [
            _validation_example(example) for example in missing_signal_examples
        ],
        "false_positive_examples": [
            _validation_example(example) for example in false_positive_examples
        ],
        "expected_mismatch_examples": expected_mismatch_examples,
        "regex_errors": regex_errors,
    }


def _parser_required_signal_examples(
    examples: list[DistillationExample],
) -> list[DistillationExample]:
    return [example for example in examples if _is_parser_required_signal(example)]


def _parser_excluded_signal_examples(
    examples: list[DistillationExample],
) -> list[DistillationExample]:
    return [
        example
        for example in examples
        if example.is_signal and not _is_parser_required_signal(example)
    ]


def _is_parser_required_signal(example: DistillationExample) -> bool:
    if not example.is_signal:
        return False
    if example.expected is not None:
        return True
    text = example.text or ""
    return bool(
        _PARSER_SYMBOL_CLUE_PATTERN.search(text)
        and _PARSER_SIDE_CLUE_PATTERN.search(text)
    )


def _parser_prompt_examples(
    examples: list[DistillationExample],
) -> list[DistillationExample]:
    required = _parser_required_signal_examples(examples)
    guards = _parser_guard_examples(examples)
    return [*required, *guards]


def _parser_guard_examples(
    examples: list[DistillationExample],
) -> list[DistillationExample]:
    guards = [example for example in examples if not example.is_signal]
    return sorted(
        guards,
        key=lambda example: (-_parser_guard_score(example), example.message_id),
    )[:_PARSER_GUARD_EXAMPLE_LIMIT]


def _parser_guard_score(example: DistillationExample) -> int:
    text = example.text or ""
    score = 0
    if _PARSER_SYMBOL_CLUE_PATTERN.search(text):
        score += 4
    if _PARSER_SIDE_CLUE_PATTERN.search(text):
        score += 4
    if _PARSER_GUARD_CLUE_PATTERN.search(text):
        score += 2
    return score


def _compile_parser_patterns(parser_rules: list[ParserRule]) -> list[dict]:
    regex_errors = []
    for rule in parser_rules:
        for pattern in rule.patterns:
            try:
                re.compile(pattern, re.IGNORECASE | re.DOTALL)
            except re.error as error:
                regex_errors.append(
                    {
                        "rule_id": rule.rule_id,
                        "pattern": pattern,
                        "error": str(error),
                    }
                )
    return regex_errors


def _parse_predictions(
    examples: list[DistillationExample], parser_rules: list[ParserRule]
) -> dict[int, TradeIntent]:
    predictions = {}
    for example in examples:
        intent = _parse_example(example, parser_rules)
        if intent is not None:
            predictions[example.message_id] = intent
    return predictions


def _parse_example(
    example: DistillationExample, parser_rules: list[ParserRule]
) -> TradeIntent | None:
    text = example.text or ""
    for rule in parser_rules:
        intent = parse(rule, text)
        if intent is not None:
            return intent
    return None


def _missing_signal_examples(
    examples: list[DistillationExample], predictions: dict[int, TradeIntent]
) -> list[DistillationExample]:
    return [
        example
        for example in examples
        if example.is_signal and example.message_id not in predictions
    ]


def _false_positive_examples(
    examples: list[DistillationExample], predictions: dict[int, TradeIntent]
) -> list[DistillationExample]:
    return [
        example
        for example in examples
        if not example.is_signal and example.message_id in predictions
    ]


def _expected_mismatch_examples(
    examples: list[DistillationExample], predictions: dict[int, TradeIntent]
) -> list[dict]:
    mismatches = []
    for example in examples:
        if example.expected is None:
            continue
        prediction = predictions.get(example.message_id)
        if prediction is None:
            continue
        fields = _expected_mismatch_fields(example.expected, prediction)
        if not fields:
            continue
        mismatches.append(
            {
                "message_id": example.message_id,
                "fields": fields,
                "expected": example.expected.model_dump(mode="json", exclude_none=True),
                "actual": prediction.model_dump(mode="json", exclude_none=True),
            }
        )
    return mismatches


def _expected_mismatch_fields(expected, prediction: TradeIntent) -> list[str]:
    fields = []
    for field in (
        "symbol",
        "side",
        "entry_type",
        "entry_low",
        "entry_high",
        "stop_loss",
        "leverage",
        "confidence",
    ):
        expected_value = getattr(expected, field)
        if expected_value is None:
            continue
        if getattr(prediction, field) != expected_value:
            fields.append(field)
    if expected.take_profits and prediction.take_profits != expected.take_profits:
        fields.append("take_profits")
    return fields


def _parser_candidate_is_valid(report: dict) -> bool:
    if report.get("candidate_error"):
        return False
    if report.get("regex_errors"):
        return False
    if report.get("missing_signal_message_ids"):
        return False
    if report.get("false_positive_message_ids"):
        return False
    return not report.get("expected_mismatch_message_ids")


def _invalid_parser_candidate_report(
    error: Exception, examples: list[DistillationExample]
) -> dict:
    report = evaluate_parser_candidate([], examples)
    report["candidate_error"] = str(error)
    return report


def _prefer_widened_filter_rule_when_still_perfect(
    rule: FilterRule, examples: list[DistillationExample]
) -> tuple[FilterRule, dict]:
    original_report = evaluate_filter_candidate(rule.include_patterns, examples)
    widened_patterns = _widen_literal_include_patterns(rule.include_patterns)
    if widened_patterns == rule.include_patterns:
        return rule, original_report
    widened_report = evaluate_filter_candidate(widened_patterns, examples)
    if not _filter_candidate_is_perfect(widened_report):
        return rule, original_report
    widened_report["widened_from_include_patterns"] = rule.include_patterns
    return rule.model_copy(
        update={"include_patterns": widened_patterns}
    ), widened_report


def _widen_literal_include_patterns(include_patterns: list[str]) -> list[str]:
    return [_widen_literal_include_pattern(pattern) for pattern in include_patterns]


def _widen_literal_include_pattern(pattern: str) -> str:
    flag_prefix, literal = _split_inline_flag_prefix(pattern)
    if _contains_regex_meta(literal):
        return pattern
    widened = _strip_leading_decorative_prefix(literal)
    if not widened:
        return pattern
    return f"{flag_prefix}{widened}"


def _split_inline_flag_prefix(pattern: str) -> tuple[str, str]:
    match = _INLINE_FLAG_PATTERN.match(pattern)
    if match is None:
        return "", pattern
    return match.group(1), pattern[match.end() :]


def _contains_regex_meta(pattern: str) -> bool:
    return any(char in _REGEX_META_CHARS for char in pattern)


def _strip_leading_decorative_prefix(pattern: str) -> str:
    remaining = pattern
    while remaining:
        stripped = remaining.lstrip()
        if stripped != remaining:
            remaining = stripped
            continue
        keycap_match = _KEYCAP_PREFIX_PATTERN.match(remaining)
        if keycap_match is not None:
            remaining = remaining[keycap_match.end() :]
            continue
        char = remaining[0]
        if not _is_decorative_prefix_char(char):
            return remaining
        remaining = remaining[1:]
    return remaining


def _is_decorative_prefix_char(char: str) -> bool:
    if char.isalnum() or char == "_":
        return False
    category = unicodedata.category(char)
    return category[0] in {"M", "P", "S"}


def _label_lines(examples: list[DistillationExample]) -> str:
    lines = []
    for example in examples:
        line = f"- message {example.message_id}: label={example.label.value}"
        line += f"\n  text={json.dumps(example.text or '', ensure_ascii=False)}"
        if example.expected is not None:
            line += (
                f"\n  expected={example.expected.model_dump_json(exclude_none=True)}"
            )
        lines.append(line)
    return "\n".join(lines)


def _parser_label_lines(examples: list[DistillationExample]) -> str:
    lines = []
    for example in examples:
        text_limit = (
            _PARSER_SIGNAL_TEXT_LIMIT if example.is_signal else _PARSER_GUARD_TEXT_LIMIT
        )
        text = json.dumps(_truncate(example.text or "", text_limit), ensure_ascii=False)
        line = f"- message {example.message_id}: label={example.label.value}"
        line += f"\n  text={text}"
        if example.expected is not None:
            line += (
                f"\n  expected={example.expected.model_dump_json(exclude_none=True)}"
            )
        lines.append(line)
    return "\n".join(lines)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _filter_prompt(examples: list[DistillationExample]) -> str:
    return (
        "Distil include-only regex patterns for the labelled examples. A message is "
        "predicted signal if any include_pattern matches its text. The backend will "
        "perform all validation and reject any candidate below 100% labelled-example "
        "accuracy. Return exactly this JSON shape and no other keys: "
        '{"include_patterns": ["..."]}. Do not return filter_rule, parser_rules, '
        "exclude_patterns, display metadata, recall targets, or self-check fields. "
        "Prefer the smallest readable set of regex patterns that exactly separates "
        "label=signal from label=noise and label=modifier. "
        "Only output JSON.\n\n"
        f"Labeled examples:\n{_label_lines(examples)}"
    )


def _filter_retry_prompt(
    examples: list[DistillationExample], previous_report: dict
) -> str:
    previous_patterns = json.dumps(
        previous_report.get("include_patterns", []), ensure_ascii=False
    )
    regex_errors = json.dumps(
        previous_report.get("regex_errors", []), ensure_ascii=False
    )
    false_positives = _feedback_lines(
        examples, previous_report.get("false_positive_message_ids", [])
    )
    false_negatives = _feedback_lines(
        examples, previous_report.get("false_negative_message_ids", [])
    )
    return (
        "Revise the include-only regex patterns. The previous candidate failed "
        "deterministic backend validation. Return exactly this JSON shape and no "
        'other keys: {"include_patterns": ["..."]}. '
        f"Previous include_patterns: {previous_patterns}\n"
        f"Previous accuracy: {previous_report.get('accuracy')}%\n"
        f"Candidate error: {previous_report.get('candidate_error') or 'none'}\n"
        f"Regex errors: {regex_errors}\n\n"
        "Fix these false positives by making patterns more specific:\n"
        f"{false_positives}\n\n"
        "Fix these false negatives by covering the missed signal language:\n"
        f"{false_negatives}\n\n"
        f"Labeled examples:\n{_label_lines(examples)}"
    )


def _feedback_lines(examples: list[DistillationExample], message_ids: list[int]) -> str:
    if not message_ids:
        return "- none"
    examples_by_message_id = {example.message_id: example for example in examples}
    return "\n".join(
        _feedback_line(examples_by_message_id[message_id])
        for message_id in message_ids
        if message_id in examples_by_message_id
    )


def _feedback_line(example: DistillationExample) -> str:
    text = json.dumps(example.text or "", ensure_ascii=False)
    return f"- message {example.message_id}: {text}"


def _parser_prompt(examples: list[DistillationExample]) -> str:
    return (
        "Distil PRECISION-FIRST ParserRules for parser-required examples. The backend "
        "will compile the regexes, apply them with the deterministic parser, reject "
        "rules that miss parser-required signal examples, reject rules that parse "
        "noise/modifiers, and verify expected fields when an expected object is "
        "present. "
        "Return only parser rules; do not return filter_rule.\n\n"
        "Parser-required examples are labelled signal messages with instrument + "
        "direction clues. Labelled signal lifecycle updates without direction are "
        "not parser-required because ExtractedSignal requires symbol and side.\n\n"
        "ParserRule contract:\n"
        "- patterns are Python regex strings with named groups.\n"
        "- field_map maps named groups onto these targets only: symbol, side, entry, "
        "entry_low, entry_high, stop_loss, take_profit, leverage, confidence.\n"
        "- symbol and side are compulsory; a match without both is rejected.\n"
        "- side_aliases maps every captured side token, lower-case, to LONG or SHORT.\n"
        "- if there are multiple take profits, capture each with its own named group "
        "and map each group to take_profit.\n"
        "- if the message has an entry range, capture entry_low and entry_high.\n"
        "- if the message has one entry price, capture entry.\n"
        "- if no entry is present, omit entry groups so the parser records MARKET.\n"
        "- signal shapes may differ inside one feed; use multiple ordered patterns "
        "when the formats differ.\n\n"
        'Return JSON {"parser_rules": [{"patterns": [...], "field_map": {...}, '
        '"side_aliases": {...}}]} and no other keys.\n\n'
        f"Parser prompt examples:\n{_parser_label_lines(examples)}"
    )


def _parser_retry_prompt(
    examples: list[DistillationExample], previous_report: dict
) -> str:
    return (
        "Previous parser candidate failed deterministic validation. Revise the "
        "ParserRules and return exactly this JSON shape with no other keys: "
        '{"parser_rules": [{"patterns": [...], "field_map": {...}, '
        '"side_aliases": {...}}]}.\n\n'
        "Validation report:\n"
        f"{json.dumps(previous_report, ensure_ascii=False, indent=2, default=str)}\n\n"
        "Fix missing signal examples by covering their format. Fix false positives "
        "by making patterns more specific. Fix expected mismatches by mapping the "
        "named groups to the right fields.\n\n"
        "Parser prompt examples:\n"
        f"{_parser_label_lines(_parser_prompt_examples(examples))}"
    )


class AnthropicDistiller(RuleDistiller):
    """Anthropic-backed rule distiller over an injected prompt runner."""

    def __init__(
        self,
        runner: Callable[[str], str],
        version: int = 1,
        prompt_auditor: PromptAuditor | None = None,
        response_auditor: PromptAuditor | None = None,
        validation_auditor: ValidationAuditor | None = None,
        parser_skip_auditor: PromptAuditor | None = None,
        max_filter_attempts: int = _FILTER_MAX_ATTEMPTS,
        max_parser_attempts: int = _PARSER_MAX_ATTEMPTS,
    ) -> None:
        self._runner = runner
        self._version = version
        self._prompt_auditor = prompt_auditor
        self._response_auditor = response_auditor
        self._validation_auditor = validation_auditor
        self._parser_skip_auditor = parser_skip_auditor
        self._max_filter_attempts = max_filter_attempts
        self._max_parser_attempts = max_parser_attempts

    def distill_filter(self, examples: list[DistillationExample]) -> FilterRule:
        if not examples:
            raise ValueError("no labels to distill")
        report = evaluate_filter_candidate([], examples)
        for attempt in range(1, self._max_filter_attempts + 1):
            prompt_kind = f"filter-attempt-{attempt}"
            prompt = (
                _filter_prompt(examples)
                if attempt == 1
                else _filter_retry_prompt(examples, report)
            )
            filter_rule, report = self._distill_filter_candidate(
                examples, prompt_kind, prompt
            )
            self._audit_validation(prompt_kind, report, examples)
            if _filter_candidate_is_perfect(report):
                return filter_rule
        raise FilterDistillationError(report)

    def distill_parsers(self, examples: list[DistillationExample]) -> list[ParserRule]:
        if not examples:
            raise ValueError("no labels to distill")
        parser_required_examples = _parser_required_signal_examples(examples)
        if not parser_required_examples:
            self._audit_parser_skip(examples)
            return []
        report = evaluate_parser_candidate([], examples)
        prompt_examples = _parser_prompt_examples(examples)
        for attempt in range(1, self._max_parser_attempts + 1):
            prompt_kind = f"parser-attempt-{attempt}"
            prompt = (
                _parser_prompt(prompt_examples)
                if attempt == 1
                else _parser_retry_prompt(examples, report)
            )
            parser_rules, report = self._distill_parser_candidate(
                examples,
                prompt_examples,
                [example.id for example in parser_required_examples],
                prompt_kind,
                prompt,
            )
            self._audit_validation(prompt_kind, report, examples)
            if _parser_candidate_is_valid(report):
                return parser_rules
        raise ParserDistillationError(report)

    def _distill_filter_candidate(
        self, examples: list[DistillationExample], prompt_kind: str, prompt: str
    ) -> tuple[FilterRule | None, dict]:
        stdout = self._run_prompt(examples, prompt_kind, prompt)
        try:
            filter_rule = parse_filter_distiller_output(
                stdout,
                channel_id=examples[0].channel_id,
                label_ids=[example.id for example in examples],
                version=self._version,
            )
        except Exception as error:
            return None, _invalid_filter_candidate_report(error, examples)
        return _prefer_widened_filter_rule_when_still_perfect(filter_rule, examples)

    def _distill_parser_candidate(
        self,
        examples: list[DistillationExample],
        prompt_examples: list[DistillationExample],
        label_ids: list,
        prompt_kind: str,
        prompt: str,
    ) -> tuple[list[ParserRule], dict]:
        stdout = self._run_prompt(prompt_examples, prompt_kind, prompt)
        try:
            parser_rules = parse_parser_distiller_output(
                stdout,
                channel_id=examples[0].channel_id,
                label_ids=label_ids,
                version=self._version,
            )
        except Exception as error:
            return [], _invalid_parser_candidate_report(error, examples)
        return parser_rules, evaluate_parser_candidate(parser_rules, examples)

    def _run_prompt(
        self, examples: list[DistillationExample], prompt_kind: str, prompt: str
    ) -> str:
        if not examples:
            raise ValueError("no labels to distill")
        if self._prompt_auditor is not None:
            self._prompt_auditor(prompt_kind, prompt, examples)
        try:
            stdout = self._runner(prompt)
        except Exception as error:
            if self._response_auditor is not None:
                self._response_auditor(
                    prompt_kind, f"{type(error).__name__}: {error}", examples
                )
            raise
        if self._response_auditor is not None:
            self._response_auditor(prompt_kind, stdout, examples)
        return stdout

    def _audit_validation(
        self, prompt_kind: str, report: dict, examples: list[DistillationExample]
    ) -> None:
        if self._validation_auditor is not None:
            self._validation_auditor(prompt_kind, report, examples)

    def _audit_parser_skip(self, examples: list[DistillationExample]) -> None:
        if self._parser_skip_auditor is not None:
            self._parser_skip_auditor(
                "parser",
                "parser distillation skipped because parser_required_signal_count=0",
                examples,
            )
