"""Cross-cutting precision/recall harness over the committed golden corpus.

Distilled rules (FakeDistiller over the canned LLM output) are re-applied to the
fixture messages; reproducing the labels means filter recall + parser precision
hold on the GoldenLabel oracle (test-plan §5; denominator = GoldenLabel).
"""

from pathlib import Path

from corpus import load_labels, load_messages
from fakes import FakeDistiller

from verasig.services.distillation.evaluation import evaluate

_FIXTURES = Path(__file__).parent.parent / "fixtures"
_DISTILL = (_FIXTURES / "cli" / "distill_pilot.txt").read_text(encoding="utf-8")


def _report():
    messages = load_messages(_FIXTURES / "messages" / "pilot.jsonl")
    labels = load_labels(_FIXTURES / "labels" / "pilot.jsonl", channel_id=7)
    distiller = FakeDistiller(_DISTILL)
    filter_rule = distiller.distill_filter(labels)
    parser_rules = distiller.distill_parsers(labels)
    return evaluate(messages, labels, filter_rule, parser_rules), labels


def test_corpus_has_a_meaningful_signal_denominator():
    _, labels = _report()
    signals = sum(1 for label in labels if label.is_signal)
    assert signals >= 15  # meaningful >=0.95 denominator
    assert len(labels) >= 30  # signals + chatter


def test_filter_recall_meets_quality_gate():
    report, _ = _report()
    assert report.filter_recall >= 0.95  # ADR 0005 candidate gate (vs GoldenLabel)


def test_parser_precision_meets_quality_gate():
    report, _ = _report()
    assert report.parser_precision >= 0.95


def test_parser_recall_is_reported_not_gated():
    report, _ = _report()
    assert 0.0 <= report.parser_recall <= 1.0  # measured + reported
