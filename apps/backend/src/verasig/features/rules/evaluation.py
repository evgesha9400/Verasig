"""Precision/recall harness over a labeled corpus (test-plan §5; ADR 0005).

Pure + offline. Filter **recall** is measured on signal `GoldenLabel.label`s (the
advisory gate's miss-rate; denominator = GoldenLabel, not the candidate subset).
Parser **precision** is measured on the required `expected` fields (symbol+side)
of the messages the parser extracts from; parser **recall** is reported, not
gated.
"""

from dataclasses import dataclass

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel
from verasig.domain.message import RawTelegramMessage
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import TradeIntent
from verasig.features.signals.deterministic_parser import parse
from verasig.features.sources.candidate_filter import apply_filter_rule


@dataclass(frozen=True)
class EvalReport:
    filter_recall: float
    parser_precision: float
    parser_recall: float
    signal_count: int
    extracted_count: int


def _ratio(numerator: int, denominator: int) -> float:
    return 1.0 if denominator == 0 else numerator / denominator


def filter_recall(
    messages: list[RawTelegramMessage], labels: list[GoldenLabel], rule: FilterRule
) -> float:
    signal_ids = {label.message_id for label in labels if label.is_signal}
    flagged = {
        message.message_id
        for message in messages
        if message.text and apply_filter_rule(rule, message.text)
    }
    return _ratio(len(signal_ids & flagged), len(signal_ids))


def _parse_message(
    message: RawTelegramMessage, parser_rules: list[ParserRule]
) -> TradeIntent | None:
    for rule in parser_rules:
        intent = parse(rule, message.text or "")
        if intent is not None:
            return intent
    return None


def _is_correct(label: GoldenLabel | None, signal: TradeIntent) -> bool:
    if label is None or not label.is_signal or label.expected is None:
        return False
    return signal.symbol == label.expected.symbol and signal.side == label.expected.side


def _parse_predictions(
    messages: list[RawTelegramMessage], parser_rules: list[ParserRule]
) -> dict[int, TradeIntent]:
    predictions = {}
    for message in messages:
        if not message.text:
            continue
        signal = _parse_message(message, parser_rules)
        if signal is None:
            continue
        predictions[message.message_id] = signal
    return predictions


def evaluate(
    messages: list[RawTelegramMessage],
    labels: list[GoldenLabel],
    filter_rule: FilterRule,
    parser_rules: list[ParserRule],
) -> EvalReport:
    labels_by_id = {label.message_id: label for label in labels}
    signal_ids = {label.message_id for label in labels if label.is_signal}
    predictions = _parse_predictions(messages, parser_rules)
    true_positives = sum(
        1
        for message_id, signal in predictions.items()
        if _is_correct(labels_by_id.get(message_id), signal)
    )
    return EvalReport(
        filter_recall=filter_recall(messages, labels, filter_rule),
        parser_precision=_ratio(true_positives, len(predictions)),
        parser_recall=_ratio(true_positives, len(signal_ids)),
        signal_count=len(signal_ids),
        extracted_count=len(predictions),
    )
