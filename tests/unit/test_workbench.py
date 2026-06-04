from datetime import datetime, timezone
from pathlib import Path

from fakes import FakeDistiller

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel
from verasig.domain.message import RawTelegramMessage
from verasig.domain.parser_rule import ParserRule
from verasig.services.distillation.workbench import (
    WorkbenchViews,
    distil_step,
    partition,
    recall_meter,
    residue,
)

_DISTILL = (
    Path(__file__).parent.parent / "fixtures" / "cli" / "distill_pilot.txt"
).read_text(encoding="utf-8")


def _instant() -> datetime:
    return datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)


def _messages(count: int) -> list[RawTelegramMessage]:
    return [
        RawTelegramMessage(
            channel_id=7,
            message_id=i,
            text=f"msg {i}",
            posted_at=_instant(),
            captured_at=_instant(),
            has_media=False,
            raw_payload={},
        )
        for i in range(1, count + 1)
    ]


def test_partition_splits_candidates_unflagged_and_drift():
    messages = _messages(6)
    views = partition(messages, candidate_ids={1, 2}, drift_ids={5}, audit_size=2)
    assert isinstance(views, WorkbenchViews)
    assert {m.message_id for m in views.candidates} == {1, 2}
    assert {m.message_id for m in views.unflagged} == {3, 4, 5, 6}
    assert {m.message_id for m in views.drift} == {5}


def test_audit_is_a_bounded_sample_of_unflagged():
    messages = _messages(10)
    views = partition(messages, candidate_ids=set(), drift_ids=set(), audit_size=3)
    assert len(views.audit) == 3
    unflagged_ids = {m.message_id for m in views.unflagged}
    assert all(m.message_id in unflagged_ids for m in views.audit)


def test_residue_is_unlabeled_messages_and_shrinks_as_labels_grow():
    messages = _messages(5)
    assert len(residue(messages, labeled_ids=set())) == 5
    assert len(residue(messages, labeled_ids={1, 2})) == 3


def test_recall_meter_reports_filter_recall_against_labels():
    messages = [
        RawTelegramMessage(
            channel_id=7,
            message_id=1,
            text="BTC long",
            posted_at=_instant(),
            captured_at=_instant(),
            has_media=False,
            raw_payload={},
        ),
        RawTelegramMessage(
            channel_id=7,
            message_id=2,
            text="gm frens",
            posted_at=_instant(),
            captured_at=_instant(),
            has_media=False,
            raw_payload={},
        ),
    ]
    labels = [
        GoldenLabel(channel_id=7, message_id=1, is_signal=True),
        GoldenLabel(channel_id=7, message_id=2, is_signal=False),
    ]
    rule = FilterRule(rule_id="r", include_patterns=[r"(?i)\blong\b"])
    assert recall_meter(messages, labels, rule) == 1.0  # the one signal is flagged


def test_distil_step_returns_filter_and_parser_rules():
    labels = [GoldenLabel(channel_id=7, message_id=1, is_signal=True)]
    filter_rule, parser_rules = distil_step(labels, FakeDistiller(_DISTILL))
    assert isinstance(filter_rule, FilterRule)
    assert parser_rules and isinstance(parser_rules[0], ParserRule)
