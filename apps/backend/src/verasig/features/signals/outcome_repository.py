"""Outcome repository functions."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.drift import ParserDriftWarning
from verasig.domain.extraction_outcome import ExtractOutcome
from verasig.domain.signal import ExtractedSignal, UnrecognizedSignal
from verasig.storage.models import (
    ExtractedSignalRow,
    ParserDriftWarningRow,
    RawSignalEventRow,
    UnrecognizedSignalRow,
)


def _str_list(values: list) -> list[str]:
    return [str(value) for value in values]


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


def _with_user_id(values: dict, user_id: UUID) -> dict:
    return {**values, "user_id": user_id}


def insert_extracted_signals(
    session: Session, signals: list[ExtractedSignal], user_id: UUID
) -> int:
    if not signals:
        return 0
    statement = (
        pg_insert(ExtractedSignalRow)
        .values(
            [_with_user_id(_extracted_values(signal), user_id) for signal in signals]
        )
        .returning(ExtractedSignalRow.id)
    )
    return len(session.execute(statement).fetchall())


def read_extracted_signals(
    session: Session, channel_id: int, user_id: UUID
) -> list[ExtractedSignal]:
    rows = session.scalars(
        select(ExtractedSignalRow).where(
            ExtractedSignalRow.channel_id == channel_id,
            ExtractedSignalRow.user_id == user_id,
        )
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
    session: Session, items: list[UnrecognizedSignal], user_id: UUID
) -> int:
    if not items:
        return 0
    statement = (
        pg_insert(UnrecognizedSignalRow)
        .values([_with_user_id(_unrecognized_values(item), user_id) for item in items])
        .returning(UnrecognizedSignalRow.id)
    )
    return len(session.execute(statement).fetchall())


def read_unrecognized_signals(
    session: Session, channel_id: int, user_id: UUID
) -> list[UnrecognizedSignal]:
    rows = session.scalars(
        select(UnrecognizedSignalRow)
        .join(RawSignalEventRow, UnrecognizedSignalRow.event_id == RawSignalEventRow.id)
        .where(
            RawSignalEventRow.channel_id == channel_id,
            UnrecognizedSignalRow.user_id == user_id,
        )
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


def _parser_drift_values(
    drift: ParserDriftWarning, fallback_signal_id: UUID, user_id: UUID
) -> dict:
    return {
        "id": drift.id,
        "user_id": user_id,
        "event_id": drift.event_id,
        "channel_id": drift.channel_id,
        "deterministic_result": drift.deterministic_result,
        "fallback_result": drift.fallback_result,
        "fallback_signal_id": fallback_signal_id,
        "created_at": drift.created_at,
    }


def _excluded_except(statement, row_type, keep: set[str]) -> dict:
    return {
        column.name: getattr(statement.excluded, column.name)
        for column in row_type.__table__.columns
        if column.name not in keep
    }


def _delete_outcome_row(
    session: Session, row_type, event_id: UUID, user_id: UUID
) -> None:
    session.execute(
        delete(row_type).where(
            row_type.event_id == event_id,
            row_type.user_id == user_id,
        )
    )


def _upsert_extracted_signal(
    session: Session, signal: ExtractedSignal, user_id: UUID
) -> UUID:
    statement = pg_insert(ExtractedSignalRow).values(
        _with_user_id(_extracted_values(signal), user_id)
    )
    statement = statement.on_conflict_do_update(
        index_elements=["user_id", "event_id"],
        set_=_excluded_except(
            statement, ExtractedSignalRow, {"id", "user_id", "event_id"}
        ),
    ).returning(ExtractedSignalRow.id)
    return session.execute(statement).scalar_one()


def _upsert_unrecognized_signal(
    session: Session, item: UnrecognizedSignal, user_id: UUID
) -> None:
    statement = pg_insert(UnrecognizedSignalRow).values(
        _with_user_id(_unrecognized_values(item), user_id)
    )
    statement = statement.on_conflict_do_update(
        index_elements=["user_id", "event_id"],
        set_=_excluded_except(
            statement, UnrecognizedSignalRow, {"id", "user_id", "event_id"}
        ),
    )
    session.execute(statement)


def _upsert_parser_drift(
    session: Session,
    drift: ParserDriftWarning,
    fallback_signal_id: UUID,
    user_id: UUID,
) -> None:
    statement = pg_insert(ParserDriftWarningRow).values(
        _parser_drift_values(drift, fallback_signal_id, user_id)
    )
    statement = statement.on_conflict_do_update(
        index_elements=["user_id", "event_id"],
        set_=_excluded_except(
            statement, ParserDriftWarningRow, {"id", "user_id", "event_id"}
        ),
    )
    session.execute(statement)


def _record_extracted(
    session: Session,
    signal: ExtractedSignal,
    drift_warnings: list,
    user_id: UUID,
) -> None:
    stored_id = _upsert_extracted_signal(session, signal, user_id)
    _delete_outcome_row(session, UnrecognizedSignalRow, signal.event_id, user_id)
    if drift_warnings:
        _upsert_parser_drift(session, drift_warnings[0], stored_id, user_id)
    else:
        _delete_outcome_row(session, ParserDriftWarningRow, signal.event_id, user_id)


def _record_unrecognized(
    session: Session, item: UnrecognizedSignal, user_id: UUID
) -> None:
    _upsert_unrecognized_signal(session, item, user_id)
    _delete_outcome_row(session, ExtractedSignalRow, item.event_id, user_id)
    _delete_outcome_row(session, ParserDriftWarningRow, item.event_id, user_id)


def record_outcome(session: Session, outcome: ExtractOutcome, user_id: UUID) -> None:
    """Recompute one event's projection: upsert the winner, drop the loser + drift."""
    if outcome.signal is not None:
        _record_extracted(session, outcome.signal, outcome.drift_warnings, user_id)
    elif outcome.unrecognized is not None:
        _record_unrecognized(session, outcome.unrecognized, user_id)
