from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import LabelKind
from verasig.features.rules.repository import read_filter_rules
from verasig.features.sources.candidate_filter import apply_filter_rule
from verasig.storage.models import GoldenLabelRow, RawMessageRow


def present_rules(session: Session, user_id: UUID, channel_id: int) -> list[dict]:
    labels = _signal_label_texts(session, user_id, channel_id)
    rules = read_filter_rules(session, channel_id, user_id)
    return [
        _present_pattern(rule, index, pattern, labels)
        for rule in rules
        for index, pattern in enumerate(rule.include_patterns)
    ]


def _signal_label_texts(session: Session, user_id: UUID, channel_id: int) -> list[str]:
    rows = session.execute(
        select(RawMessageRow.text)
        .join(
            GoldenLabelRow,
            (GoldenLabelRow.channel_id == RawMessageRow.channel_id)
            & (GoldenLabelRow.message_id == RawMessageRow.message_id),
        )
        .where(
            GoldenLabelRow.user_id == user_id,
            GoldenLabelRow.channel_id == channel_id,
            GoldenLabelRow.label == LabelKind.SIGNAL.value,
        )
    ).all()
    return [text for (text,) in rows if text]


def _present_pattern(
    rule: FilterRule, index: int, pattern: str, signal_texts: list[str]
) -> dict:
    display = rule.display[index] if index < len(rule.display) else {}
    single_pattern_rule = rule.model_copy(update={"include_patterns": [pattern]})
    matches = sum(
        1 for text in signal_texts if apply_filter_rule(single_pattern_rule, text)
    )
    match = round((matches / len(signal_texts)) * 100, 1) if signal_texts else 0.0
    return {
        "id": f"{rule.rule_id}:{index}",
        "label": display.get("label") or pattern,
        "detail": display.get("detail") or pattern,
        "match": match,
    }
