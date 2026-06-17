from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from verasig.domain.drift import FilterDriftWarning, MissDiscoveredBy
from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel, LabelKind
from verasig.features.feeds import feed_repository
from verasig.features.feeds.candidate_filter import apply_filter_rule
from verasig.features.feeds.message_views import (
    project_message,
    read_replies_by_message_id,
)
from verasig.features.rules import drift_repository
from verasig.features.rules import repository as rule_repository
from verasig.features.rules.repository import upsert_labels
from verasig.storage.models import (
    GoldenLabelRow,
    RawMessageRow,
    RawSignalEventRow,
)

MIN_VERDICTS = 6


class TooFewVerdictsError(ValueError):
    pass


class Prediction(StrEnum):
    SIGNAL = "signal"
    NOISE = "noise"


class Verdict(StrEnum):
    CORRECT = "correct"
    WRONG = "wrong"


type VerdictInput = dict[str, str]


def verification_samples(session: Session, user_id: UUID, channel_id: int) -> dict:
    rows = _sample_rows(session, user_id, channel_id)
    channel = feed_repository.read_feed(session, user_id, channel_id)
    replies = read_replies_by_message_id(session, user_id, channel_id, rows)
    rules = rule_repository.read_filter_rules(session, channel_id, user_id)
    subscription = feed_repository.read_feed(session, user_id, channel_id)
    return {
        "attempt": subscription.verify_attempt if subscription else 1,
        "samples": [
            {
                **project_message(
                    row, channel, replies.get(row.reply_to_external_message_id)
                ),
                "predicted": predict_sample(rules, row).value,
            }
            for row in rows
        ],
    }


def apply_verdicts(
    session: Session, user_id: UUID, channel_id: int, verdicts: list[VerdictInput]
) -> tuple[bool, list[str]]:
    if len(verdicts) < MIN_VERDICTS:
        raise TooFewVerdictsError
    rows = _rows_by_message_id(session, user_id, channel_id, _message_ids(verdicts))
    rules = rule_repository.read_filter_rules(session, channel_id, user_id)
    labels = flip_wrong_predictions_into_labels(
        user_id, channel_id, verdicts, rows, rules
    )
    upsert_labels(session, labels)
    session.flush()
    emit_drift_for_missed_signals(
        session,
        user_id,
        channel_id,
        verdicts,
        rows,
        rules,
        _label_ids_by_message_id(session, user_id, channel_id, labels),
    )
    passed, misclassified = decide_pass(verdicts)
    if passed:
        feed_repository.set_status(session, user_id, channel_id, "verified")
        return True, []
    if misclassified:
        feed_repository.bump_verify_attempt(session, user_id, channel_id)
    return False, misclassified


def _sample_rows(
    session: Session, user_id: UUID, channel_id: int, limit: int = 20
) -> list[RawMessageRow]:
    labeled = (
        select(GoldenLabelRow.external_message_id)
        .where(
            GoldenLabelRow.user_id == user_id,
            GoldenLabelRow.external_id == channel_id,
        )
        .subquery()
    )
    return list(
        session.scalars(
            select(RawMessageRow)
            .join(
                RawSignalEventRow,
                (RawSignalEventRow.user_id == RawMessageRow.user_id)
                & (RawSignalEventRow.external_id == RawMessageRow.external_id)
                & (
                    RawSignalEventRow.external_message_id
                    == RawMessageRow.external_message_id
                ),
            )
            .where(
                RawMessageRow.user_id == user_id,
                RawMessageRow.external_id == channel_id,
                RawMessageRow.external_message_id.not_in(
                    select(labeled.c.external_message_id)
                ),
            )
            .order_by(RawMessageRow.posted_at, RawMessageRow.external_message_id)
            .limit(limit)
        )
    )


def _message_ids(verdicts: list[VerdictInput]) -> list[int]:
    return [int(verdict["messageId"]) for verdict in verdicts]


def _rows_by_message_id(
    session: Session, user_id: UUID, channel_id: int, message_ids: list[int]
) -> dict[int, RawMessageRow]:
    rows = session.scalars(
        select(RawMessageRow).where(
            RawMessageRow.user_id == user_id,
            RawMessageRow.external_id == channel_id,
            RawMessageRow.external_message_id.in_(message_ids),
        )
    ).all()
    return {row.external_message_id: row for row in rows}


def predict_sample(rules: list[FilterRule], row: RawMessageRow) -> Prediction:
    return _predict_text(rules, row.text)


def _predict_text(rules: list[FilterRule], text: str | None) -> Prediction:
    if text is None:
        return Prediction.NOISE
    if any(apply_filter_rule(rule, text) for rule in rules):
        return Prediction.SIGNAL
    return Prediction.NOISE


def flip_wrong_predictions_into_labels(
    user_id: UUID,
    channel_id: int,
    verdicts: list[VerdictInput],
    rows: dict[int, RawMessageRow],
    rules: list[FilterRule],
) -> list[GoldenLabel]:
    return [
        GoldenLabel(
            user_id=user_id,
            channel_id=channel_id,
            message_id=message_id,
            label=_label_from_verdict(predict_sample(rules, rows[message_id]), verdict),
            labeled_at=datetime.now(tz=UTC),
        )
        for verdict in verdicts
        if (message_id := int(verdict["messageId"])) in rows
    ]


def _label_from_verdict(prediction: Prediction, verdict: VerdictInput) -> LabelKind:
    if Verdict(verdict["verdict"]) is Verdict.CORRECT:
        return LabelKind(prediction.value)
    if prediction is Prediction.SIGNAL:
        return LabelKind.NOISE
    return LabelKind.SIGNAL


def emit_drift_for_missed_signals(
    session: Session,
    user_id: UUID,
    channel_id: int,
    verdicts: list[VerdictInput],
    rows: dict[int, RawMessageRow],
    rules: list[FilterRule],
    source_label_ids: dict[int, UUID],
) -> None:
    event_ids = _event_ids_by_message_id(
        session, user_id, channel_id, list(source_label_ids)
    )
    warnings = [
        FilterDriftWarning(
            channel_id=channel_id,
            message_id=message_id,
            filter_rule_version=_latest_filter_rule_version(rules),
            miss_discovered_by=MissDiscoveredBy.HUMAN_AUDIT,
            event_id=event_ids.get(message_id),
            source_label_id=source_label_ids.get(message_id),
        )
        for verdict in verdicts
        if (message_id := int(verdict["messageId"])) in rows
        if Verdict(verdict["verdict"]) is Verdict.WRONG
        if predict_sample(rules, rows[message_id]) is Prediction.NOISE
    ]
    drift_repository.insert_drift_warnings(session, warnings, user_id)


def _event_ids_by_message_id(
    session: Session, user_id: UUID, channel_id: int, message_ids: list[int]
) -> dict[int, UUID]:
    rows = session.execute(
        select(RawSignalEventRow.external_message_id, RawSignalEventRow.id).where(
            RawSignalEventRow.user_id == user_id,
            RawSignalEventRow.external_id == channel_id,
            RawSignalEventRow.external_message_id.in_(message_ids),
        )
    ).all()
    return {message_id: event_id for message_id, event_id in rows}


def _latest_filter_rule_version(rules) -> int | None:
    versions = [rule.version for rule in rules]
    return max(versions) if versions else None


def decide_pass(verdicts: list[VerdictInput]) -> tuple[bool, list[str]]:
    misclassified = [
        str(verdict["messageId"])
        for verdict in verdicts
        if Verdict(verdict["verdict"]) is Verdict.WRONG
    ]
    return not misclassified, misclassified


def _label_ids_by_message_id(
    session: Session, user_id: UUID, channel_id: int, labels: list[GoldenLabel]
) -> dict[int, UUID]:
    message_ids = [label.message_id for label in labels]
    rows = session.execute(
        select(GoldenLabelRow.external_message_id, GoldenLabelRow.id).where(
            GoldenLabelRow.user_id == user_id,
            GoldenLabelRow.external_id == channel_id,
            GoldenLabelRow.external_message_id.in_(message_ids),
        )
    ).all()
    return {message_id: label_id for message_id, label_id in rows}
