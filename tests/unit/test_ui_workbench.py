from datetime import datetime, timezone

from fakes import FakeExchange

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel
from verasig.domain.message import RawTelegramMessage
from verasig.ui.workbench import view_model

_EXCHANGE = FakeExchange({"BTC"})


def _instant() -> datetime:
    return datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)


def _msg(message_id: int, text: str) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=7,
        message_id=message_id,
        text=text,
        posted_at=_instant(),
        captured_at=_instant(),
        has_media=False,
        raw_payload={},
    )


_MESSAGES = [_msg(1, "BTC long"), _msg(2, "gm frens"), _msg(3, "alpha leak incoming")]
_LABELS = [
    GoldenLabel(channel_id=7, message_id=1, is_signal=True),
    GoldenLabel(channel_id=7, message_id=2, is_signal=False),
]
_FILTER = FilterRule(
    rule_id="7-filter-v1", include_patterns=[r"(?i)\blong\b", r"(?i)alpha leak"]
)


def test_view_model_flags_seed_and_filter_candidates():
    model = view_model(
        _MESSAGES, _LABELS, _FILTER, [], drift_ids=set(), exchange=_EXCHANGE
    )
    assert model["candidate_ids"] == {1, 3}  # 1 via seed/filter, 3 via filter only
    assert {m.message_id for m in model["views"].candidates} == {1, 3}
    assert {m.message_id for m in model["views"].unflagged} == {2}


def test_view_model_reports_filter_recall_against_labels():
    model = view_model(
        _MESSAGES, _LABELS, _FILTER, [], drift_ids=set(), exchange=_EXCHANGE
    )
    assert model["recall"] == 1.0  # the single signal (msg 1) is flagged


def test_view_model_residue_excludes_labeled_messages():
    model = view_model(
        _MESSAGES, _LABELS, _FILTER, [], drift_ids=set(), exchange=_EXCHANGE
    )
    assert {m.message_id for m in model["residue"]} == {3}  # 1 and 2 are labeled


def test_view_model_without_filter_rule_uses_seed_only_and_zero_recall():
    model = view_model(
        _MESSAGES, _LABELS, None, [], drift_ids=set(), exchange=_EXCHANGE
    )
    assert model["candidate_ids"] == {1}  # only the seed flags "BTC long"
    assert model["recall"] == 0.0  # no distilled filter yet


def test_view_model_surfaces_drift_messages():
    model = view_model(
        _MESSAGES, _LABELS, _FILTER, [], drift_ids={3}, exchange=_EXCHANGE
    )
    assert {m.message_id for m in model["views"].drift} == {3}
