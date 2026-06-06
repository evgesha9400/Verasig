"""Insert-only repositories for raw capture.

Messages are appended with `ON CONFLICT DO NOTHING` (idempotent on the
`(channel_id, message_id)` PK). The channel row is upserted for metadata, but
its `first_seen_at` and the `captured_through_message_id` cursor are preserved
across re-resolves — only the cursor's own monotonic advance moves it.
"""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import DeletedSignalEvidence
from verasig.domain.drift import FilterDriftWarning, ParserDriftWarning
from verasig.domain.event import RawSignalEvent
from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel
from verasig.domain.message import RawTelegramMessage
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import ExtractedSignal, UnrecognizedSignal
from verasig.services.extraction.extract_service import ExtractOutcome
from verasig.storage.models import (
    ChannelRow,
    DeletedSignalEvidenceRow,
    ExtractedSignalRow,
    FilterDriftWarningRow,
    FilterRuleRow,
    GoldenLabelRow,
    ParserDriftWarningRow,
    ParserRuleRow,
    RawMessageRow,
    RawSignalEventRow,
    UnrecognizedSignalRow,
)


def upsert_channel(session: Session, channel: TelegramChannel) -> None:
    statement = pg_insert(ChannelRow).values(**channel.model_dump())
    statement = statement.on_conflict_do_update(
        index_elements=[ChannelRow.channel_id],
        set_={
            "handle": statement.excluded.handle,
            "title": statement.excluded.title,
            "is_private": statement.excluded.is_private,
            "subscriber_count": statement.excluded.subscriber_count,
        },
    )
    session.execute(statement)


def insert_messages(session: Session, messages: list[RawTelegramMessage]) -> int:
    if not messages:
        return 0
    statement = (
        pg_insert(RawMessageRow)
        .values([message.model_dump() for message in messages])
        .on_conflict_do_nothing(
            index_elements=[RawMessageRow.channel_id, RawMessageRow.message_id]
        )
        .returning(RawMessageRow.message_id)
    )
    return len(session.execute(statement).fetchall())


def advance_cursor(session: Session, channel_id: int, through_message_id: int) -> None:
    channel = session.get(ChannelRow, channel_id)
    if through_message_id > (channel.captured_through_message_id or 0):
        channel.captured_through_message_id = through_message_id


def read_cursor(session: Session, channel_id: int) -> int | None:
    channel = session.get(ChannelRow, channel_id)
    return channel.captured_through_message_id if channel else None


def count_messages(session: Session, channel_id: int) -> int:
    return session.scalar(
        select(func.count())
        .select_from(RawMessageRow)
        .where(RawMessageRow.channel_id == channel_id)
    )


def find_channel(session: Session, reference: str | int) -> ChannelRow | None:
    handle = _reference_to_handle(reference)
    if handle is None:
        return session.get(ChannelRow, int(reference))
    return session.scalar(select(ChannelRow).where(ChannelRow.handle == handle))


def _reference_to_handle(reference: str | int) -> str | None:
    text = str(reference)
    if text.lstrip("-").isdigit():
        return None  # numeric -> look up by id
    return text.removeprefix("https://t.me/").removeprefix("t.me/").lstrip("@")


# --- Events, extraction outputs, rules, golden corpus, drift -------------------
# JSONB columns hold list/map fields as JSON-safe values (UUID/Decimal -> str);
# Pydantic coerces them back on read, so ORM rows mirror the §2-§4 contracts 1:1.


def _str_list(values: list) -> list[str]:
    return [str(value) for value in values]


def _row_to_message(row: RawMessageRow) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=row.channel_id,
        message_id=row.message_id,
        text=row.text,
        sender_id=row.sender_id,
        posted_at=row.posted_at,
        captured_at=row.captured_at,
        reply_to_message_id=row.reply_to_message_id,
        edit_date=row.edit_date,
        has_media=row.has_media,
        views=row.views,
        forwards=row.forwards,
        raw_payload=row.raw_payload,
    )


def read_message(
    session: Session, channel_id: int, message_id: int
) -> RawTelegramMessage | None:
    row = session.get(RawMessageRow, (channel_id, message_id))
    if row is None:
        return None
    return _row_to_message(row)


def read_messages(session: Session, channel_id: int) -> list[RawTelegramMessage]:
    rows = session.scalars(
        select(RawMessageRow).where(RawMessageRow.channel_id == channel_id)
    ).all()
    return [_row_to_message(row) for row in rows]


def read_message_page(
    session: Session, channel_id: int, after_message_id: int, limit: int
) -> list[RawTelegramMessage]:
    """One bounded page of messages with id > cursor (keyset pagination)."""
    rows = session.scalars(
        select(RawMessageRow)
        .where(
            RawMessageRow.channel_id == channel_id,
            RawMessageRow.message_id > after_message_id,
        )
        .order_by(RawMessageRow.message_id)
        .limit(limit)
    ).all()
    return [_row_to_message(row) for row in rows]


def candidate_message_ids(session: Session, channel_id: int) -> set[int]:
    return set(
        session.scalars(
            select(RawSignalEventRow.message_id).where(
                RawSignalEventRow.channel_id == channel_id
            )
        ).all()
    )


def insert_signal_events(session: Session, events: list[RawSignalEvent]) -> int:
    if not events:
        return 0
    statement = (
        pg_insert(RawSignalEventRow)
        .values(
            [
                {
                    "id": event.id,
                    "channel_id": event.channel_id,
                    "message_id": event.message_id,
                    "candidate_text": event.candidate_text,
                    "materialized_by": event.materialized_by.value,
                    "matched_reasons": [
                        reason.value for reason in event.matched_reasons
                    ],
                    "filter_rule_id": event.filter_rule_id,
                    "created_at": event.created_at,
                }
                for event in events
            ]
        )
        .on_conflict_do_nothing(index_elements=["channel_id", "message_id"])
        .returning(RawSignalEventRow.id)
    )
    return len(session.execute(statement).fetchall())


def read_signal_events(session: Session, channel_id: int) -> list[RawSignalEvent]:
    rows = session.scalars(
        select(RawSignalEventRow).where(RawSignalEventRow.channel_id == channel_id)
    ).all()
    return [
        RawSignalEvent(
            id=row.id,
            channel_id=row.channel_id,
            message_id=row.message_id,
            candidate_text=row.candidate_text,
            materialized_by=row.materialized_by,
            matched_reasons=row.matched_reasons,
            filter_rule_id=row.filter_rule_id,
            created_at=row.created_at,
        )
        for row in rows
    ]


def upsert_filter_rule(session: Session, rule: FilterRule) -> None:
    statement = pg_insert(FilterRuleRow).values(
        rule_id=rule.rule_id,
        channel_id=rule.channel_id,
        version=rule.version,
        include_patterns=rule.include_patterns,
        exclude_patterns=rule.exclude_patterns,
        matched_reason_template=rule.matched_reason_template,
        recall_target=rule.recall_target,
        python_filter=rule.python_filter,
        created_at=rule.created_at,
        distilled_from_label_ids=_str_list(rule.distilled_from_label_ids),
    )
    statement = statement.on_conflict_do_update(
        index_elements=[FilterRuleRow.rule_id],
        set_={
            "channel_id": statement.excluded.channel_id,
            "version": statement.excluded.version,
            "include_patterns": statement.excluded.include_patterns,
            "exclude_patterns": statement.excluded.exclude_patterns,
            "matched_reason_template": statement.excluded.matched_reason_template,
            "recall_target": statement.excluded.recall_target,
            "python_filter": statement.excluded.python_filter,
            "distilled_from_label_ids": statement.excluded.distilled_from_label_ids,
        },
    )
    session.execute(statement)


def read_filter_rules(session: Session, channel_id: int) -> list[FilterRule]:
    rows = session.scalars(
        select(FilterRuleRow).where(FilterRuleRow.channel_id == channel_id)
    ).all()
    return [
        FilterRule(
            rule_id=row.rule_id,
            channel_id=row.channel_id,
            version=row.version,
            include_patterns=row.include_patterns,
            exclude_patterns=row.exclude_patterns,
            matched_reason_template=row.matched_reason_template,
            recall_target=row.recall_target,
            python_filter=row.python_filter,
            created_at=row.created_at,
            distilled_from_label_ids=row.distilled_from_label_ids,
        )
        for row in rows
    ]


def upsert_parser_rules(session: Session, rules: list[ParserRule]) -> None:
    for rule in rules:
        statement = pg_insert(ParserRuleRow).values(
            rule_id=rule.rule_id,
            channel_id=rule.channel_id,
            version=rule.version,
            patterns=rule.patterns,
            field_map=rule.field_map,
            side_aliases={key: side.value for key, side in rule.side_aliases.items()},
            python_extractor=rule.python_extractor,
            created_at=rule.created_at,
            distilled_from_label_ids=_str_list(rule.distilled_from_label_ids),
        )
        statement = statement.on_conflict_do_update(
            index_elements=[ParserRuleRow.rule_id],
            set_={
                "channel_id": statement.excluded.channel_id,
                "version": statement.excluded.version,
                "patterns": statement.excluded.patterns,
                "field_map": statement.excluded.field_map,
                "side_aliases": statement.excluded.side_aliases,
                "python_extractor": statement.excluded.python_extractor,
                "distilled_from_label_ids": statement.excluded.distilled_from_label_ids,
            },
        )
        session.execute(statement)


def read_parser_rules(session: Session, channel_id: int) -> list[ParserRule]:
    rows = session.scalars(
        select(ParserRuleRow).where(ParserRuleRow.channel_id == channel_id)
    ).all()
    return [
        ParserRule(
            rule_id=row.rule_id,
            channel_id=row.channel_id,
            version=row.version,
            patterns=row.patterns,
            field_map=row.field_map,
            side_aliases=row.side_aliases,
            python_extractor=row.python_extractor,
            created_at=row.created_at,
            distilled_from_label_ids=row.distilled_from_label_ids,
        )
        for row in rows
    ]


def upsert_labels(session: Session, labels: list[GoldenLabel]) -> None:
    for label in labels:
        statement = pg_insert(GoldenLabelRow).values(
            id=label.id,
            channel_id=label.channel_id,
            message_id=label.message_id,
            is_signal=label.is_signal,
            expected=(
                label.expected.model_dump(mode="json") if label.expected else None
            ),
            labeled_at=label.labeled_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["channel_id", "message_id"],
            set_={
                "is_signal": statement.excluded.is_signal,
                "expected": statement.excluded.expected,
                "labeled_at": statement.excluded.labeled_at,
            },
        )
        session.execute(statement)


def read_labels(session: Session, channel_id: int) -> list[GoldenLabel]:
    rows = session.scalars(
        select(GoldenLabelRow).where(GoldenLabelRow.channel_id == channel_id)
    ).all()
    return [
        GoldenLabel(
            id=row.id,
            channel_id=row.channel_id,
            message_id=row.message_id,
            is_signal=row.is_signal,
            expected=row.expected,
            labeled_at=row.labeled_at,
        )
        for row in rows
    ]


def insert_drift_warnings(session: Session, warnings: list[FilterDriftWarning]) -> int:
    if not warnings:
        return 0
    statement = (
        pg_insert(FilterDriftWarningRow)
        .values(
            [
                {
                    "id": warning.id,
                    "channel_id": warning.channel_id,
                    "message_id": warning.message_id,
                    "filter_rule_version": warning.filter_rule_version,
                    "miss_discovered_by": warning.miss_discovered_by.value,
                    "event_id": warning.event_id,
                    "source_label_id": warning.source_label_id,
                    "created_at": warning.created_at,
                }
                for warning in warnings
            ]
        )
        .on_conflict_do_nothing(index_elements=["channel_id", "message_id"])
        .returning(FilterDriftWarningRow.id)
    )
    return len(session.execute(statement).fetchall())


def read_drift_warnings(session: Session, channel_id: int) -> list[FilterDriftWarning]:
    rows = session.scalars(
        select(FilterDriftWarningRow).where(
            FilterDriftWarningRow.channel_id == channel_id
        )
    ).all()
    return [
        FilterDriftWarning(
            id=row.id,
            channel_id=row.channel_id,
            message_id=row.message_id,
            filter_rule_version=row.filter_rule_version,
            miss_discovered_by=row.miss_discovered_by,
            event_id=row.event_id,
            source_label_id=row.source_label_id,
            created_at=row.created_at,
        )
        for row in rows
    ]


def _extracted_values(signal: ExtractedSignal) -> dict:
    return {
        "id": signal.id,
        "event_id": signal.event_id,
        "channel_id": signal.channel_id,
        "symbol": signal.symbol,
        "side": signal.side.value,
        "event_type": signal.event_type.value,
        "references_message_id": signal.references_message_id,
        "entry_type": signal.entry_type.value if signal.entry_type else None,
        "entry_low": signal.entry_low,
        "entry_high": signal.entry_high,
        "stop_loss": signal.stop_loss,
        "take_profits": _str_list(signal.take_profits),
        "leverage": signal.leverage,
        "confidence": signal.confidence,
        "extraction_method": signal.extraction_method.value,
        "rule_id": signal.rule_id,
        "extracted_at": signal.extracted_at,
    }


def insert_extracted_signals(session: Session, signals: list[ExtractedSignal]) -> int:
    if not signals:
        return 0
    statement = (
        pg_insert(ExtractedSignalRow)
        .values([_extracted_values(signal) for signal in signals])
        .returning(ExtractedSignalRow.id)
    )
    return len(session.execute(statement).fetchall())


def read_extracted_signals(session: Session, channel_id: int) -> list[ExtractedSignal]:
    rows = session.scalars(
        select(ExtractedSignalRow).where(ExtractedSignalRow.channel_id == channel_id)
    ).all()
    return [
        ExtractedSignal(
            id=row.id,
            event_id=row.event_id,
            channel_id=row.channel_id,
            symbol=row.symbol,
            side=row.side,
            event_type=row.event_type,
            references_message_id=row.references_message_id,
            entry_type=row.entry_type,
            entry_low=row.entry_low,
            entry_high=row.entry_high,
            stop_loss=row.stop_loss,
            take_profits=row.take_profits,
            leverage=row.leverage,
            confidence=row.confidence,
            extraction_method=row.extraction_method,
            rule_id=row.rule_id,
            extracted_at=row.extracted_at,
        )
        for row in rows
    ]


def _unrecognized_values(item: UnrecognizedSignal) -> dict:
    return {
        "id": item.id,
        "event_id": item.event_id,
        "reason": item.reason,
        "attempted_methods": [method.value for method in item.attempted_methods],
        "created_at": item.created_at,
    }


def insert_unrecognized_signals(
    session: Session, items: list[UnrecognizedSignal]
) -> int:
    if not items:
        return 0
    statement = (
        pg_insert(UnrecognizedSignalRow)
        .values([_unrecognized_values(item) for item in items])
        .returning(UnrecognizedSignalRow.id)
    )
    return len(session.execute(statement).fetchall())


def read_unrecognized_signals(
    session: Session, channel_id: int
) -> list[UnrecognizedSignal]:
    rows = session.scalars(
        select(UnrecognizedSignalRow)
        .join(RawSignalEventRow, UnrecognizedSignalRow.event_id == RawSignalEventRow.id)
        .where(RawSignalEventRow.channel_id == channel_id)
    ).all()
    return [
        UnrecognizedSignal(
            id=row.id,
            event_id=row.event_id,
            reason=row.reason,
            attempted_methods=row.attempted_methods,
            created_at=row.created_at,
        )
        for row in rows
    ]


def _parser_drift_values(drift: ParserDriftWarning, fallback_signal_id: UUID) -> dict:
    return {
        "id": drift.id,
        "event_id": drift.event_id,
        "channel_id": drift.channel_id,
        "deterministic_result": drift.deterministic_result,
        "fallback_result": drift.fallback_result,
        "fallback_signal_id": fallback_signal_id,
        "created_at": drift.created_at,
    }


def read_parser_drift_warnings(
    session: Session, channel_id: int
) -> list[ParserDriftWarning]:
    rows = session.scalars(
        select(ParserDriftWarningRow).where(
            ParserDriftWarningRow.channel_id == channel_id
        )
    ).all()
    return [
        ParserDriftWarning(
            id=row.id,
            event_id=row.event_id,
            channel_id=row.channel_id,
            deterministic_result=row.deterministic_result,
            fallback_result=row.fallback_result,
            fallback_signal_id=row.fallback_signal_id,
            created_at=row.created_at,
        )
        for row in rows
    ]


def _excluded_except(statement, row_type, keep: set[str]) -> dict:
    return {
        column.name: getattr(statement.excluded, column.name)
        for column in row_type.__table__.columns
        if column.name not in keep
    }


def _delete_outcome_row(session: Session, row_type, event_id: UUID) -> None:
    session.execute(delete(row_type).where(row_type.event_id == event_id))


def _upsert_extracted_signal(session: Session, signal: ExtractedSignal) -> UUID:
    statement = pg_insert(ExtractedSignalRow).values(_extracted_values(signal))
    statement = statement.on_conflict_do_update(
        index_elements=["event_id"],
        set_=_excluded_except(statement, ExtractedSignalRow, {"id", "event_id"}),
    ).returning(ExtractedSignalRow.id)
    return session.execute(statement).scalar_one()


def _upsert_unrecognized_signal(session: Session, item: UnrecognizedSignal) -> None:
    statement = pg_insert(UnrecognizedSignalRow).values(_unrecognized_values(item))
    statement = statement.on_conflict_do_update(
        index_elements=["event_id"],
        set_=_excluded_except(statement, UnrecognizedSignalRow, {"id", "event_id"}),
    )
    session.execute(statement)


def _upsert_parser_drift(
    session: Session, drift: ParserDriftWarning, fallback_signal_id: UUID
) -> None:
    statement = pg_insert(ParserDriftWarningRow).values(
        _parser_drift_values(drift, fallback_signal_id)
    )
    statement = statement.on_conflict_do_update(
        index_elements=["event_id"],
        set_=_excluded_except(statement, ParserDriftWarningRow, {"id", "event_id"}),
    )
    session.execute(statement)


def _record_extracted(
    session: Session, signal: ExtractedSignal, drift_warnings: list
) -> None:
    stored_id = _upsert_extracted_signal(session, signal)
    _delete_outcome_row(session, UnrecognizedSignalRow, signal.event_id)
    if drift_warnings:
        _upsert_parser_drift(session, drift_warnings[0], stored_id)
    else:
        _delete_outcome_row(session, ParserDriftWarningRow, signal.event_id)


def _record_unrecognized(session: Session, item: UnrecognizedSignal) -> None:
    _upsert_unrecognized_signal(session, item)
    _delete_outcome_row(session, ExtractedSignalRow, item.event_id)
    _delete_outcome_row(session, ParserDriftWarningRow, item.event_id)


def record_outcome(session: Session, outcome: ExtractOutcome) -> None:
    """Recompute one event's projection: upsert the winner, drop the loser + drift."""
    if outcome.signal is not None:
        _record_extracted(session, outcome.signal, outcome.drift_warnings)
    elif outcome.unrecognized is not None:
        _record_unrecognized(session, outcome.unrecognized)


# --- Durable, non-recomputable deletion evidence (ADR 0008) -------------------
# One row per (channel_id, message_id). The guarded upsert upgrades
# SUSPECTED->CONFIRMED only and never writes detected_at, so a same-state rescan
# is a true +0 and the first-noticed timestamp is preserved.


def _deletion_values(evidence: DeletedSignalEvidence) -> dict:
    return {
        "id": evidence.id,
        "channel_id": evidence.channel_id,
        "message_id": evidence.message_id,
        "confidence": evidence.confidence.value,
        "method": evidence.method.value,
        "original_text": evidence.original_text,
        "first_seen_at": evidence.first_seen_at,
        "detected_at": evidence.detected_at,
        "was_signal_candidate": evidence.was_signal_candidate,
    }


def upsert_deletion_evidence(
    session: Session, evidence: list[DeletedSignalEvidence]
) -> int:
    """Persist evidence; upgrade SUSPECTED->CONFIRMED only, preserving detected_at."""
    if not evidence:
        return 0
    statement = pg_insert(DeletedSignalEvidenceRow).values(
        [_deletion_values(item) for item in evidence]
    )
    statement = statement.on_conflict_do_update(
        index_elements=["channel_id", "message_id"],
        set_={
            "confidence": statement.excluded.confidence,
            "method": statement.excluded.method,
            "original_text": statement.excluded.original_text,
            "first_seen_at": statement.excluded.first_seen_at,
            "was_signal_candidate": statement.excluded.was_signal_candidate,
        },
        where=(
            (DeletedSignalEvidenceRow.confidence == "SUSPECTED")
            & (statement.excluded.confidence == "CONFIRMED")
        ),
    ).returning(DeletedSignalEvidenceRow.id)
    return len(session.execute(statement).fetchall())


def _row_to_deletion(row: DeletedSignalEvidenceRow) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        id=row.id,
        channel_id=row.channel_id,
        message_id=row.message_id,
        confidence=row.confidence,
        method=row.method,
        original_text=row.original_text,
        first_seen_at=row.first_seen_at,
        detected_at=row.detected_at,
        was_signal_candidate=row.was_signal_candidate,
    )


def read_deletion_evidence(
    session: Session, channel_id: int
) -> list[DeletedSignalEvidence]:
    rows = session.scalars(
        select(DeletedSignalEvidenceRow).where(
            DeletedSignalEvidenceRow.channel_id == channel_id
        )
    ).all()
    return [_row_to_deletion(row) for row in rows]
