"""Outcome repository functions.

An extraction "miss" is not a stored row — it is a `raw_signal_event` with no
matching `extracted_signal`. Misses are therefore recovered by anti-join, never
persisted.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.signal import ExtractedSignal
from verasig.storage.models import ExtractedSignalRow, RawSignalEventRow


def _str_list(values: list) -> list[str]:
    return [str(value) for value in values]


def _extracted_values(signal: ExtractedSignal) -> dict:
    return {
        "id": signal.id,
        "event_id": signal.event_id,
        "external_id": signal.channel_id,
        "symbol": signal.symbol,
        "side": signal.side.value,
        "event_type": signal.event_type.value,
        "entry_type": signal.entry_type.value if signal.entry_type else None,
        "entry_low": signal.entry_low,
        "entry_high": signal.entry_high,
        "stop_loss": signal.stop_loss,
        "take_profits": _str_list(signal.take_profits),
        "leverage": signal.leverage,
        "confidence": signal.confidence,
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


def read_signal_channel(session: Session, user_id: UUID, signal_id: UUID) -> int | None:
    """The channel a signal belongs to, so a single signal can be projected
    against only its own feed instead of every feed the user owns."""
    return session.scalar(
        select(ExtractedSignalRow.external_id).where(
            ExtractedSignalRow.id == signal_id,
            ExtractedSignalRow.user_id == user_id,
        )
    )


def read_extracted_signals(
    session: Session, channel_id: int, user_id: UUID
) -> list[ExtractedSignal]:
    rows = session.scalars(
        select(ExtractedSignalRow).where(
            ExtractedSignalRow.external_id == channel_id,
            ExtractedSignalRow.user_id == user_id,
        )
    ).all()
    return [
        ExtractedSignal(
            id=row.id,
            event_id=row.event_id,
            channel_id=row.external_id,
            symbol=row.symbol,
            side=row.side,
            event_type=row.event_type,
            entry_type=row.entry_type,
            entry_low=row.entry_low,
            entry_high=row.entry_high,
            stop_loss=row.stop_loss,
            take_profits=row.take_profits,
            leverage=row.leverage,
            confidence=row.confidence,
            rule_id=row.rule_id,
            extracted_at=row.extracted_at,
        )
        for row in rows
    ]


def read_unrecognized_event_ids(
    session: Session, channel_id: int, user_id: UUID
) -> list[UUID]:
    """Event ids for this feed with no extracted signal — the misses, by
    anti-join. A miss is the absence of an extraction, so it is derived here
    rather than stored."""
    has_extraction = select(ExtractedSignalRow.id).where(
        ExtractedSignalRow.user_id == RawSignalEventRow.user_id,
        ExtractedSignalRow.event_id == RawSignalEventRow.id,
    )
    statement = select(RawSignalEventRow.id).where(
        RawSignalEventRow.user_id == user_id,
        RawSignalEventRow.external_id == channel_id,
        ~has_extraction.exists(),
    )
    return list(session.scalars(statement).all())


def read_confirmed_template_keys(
    session: Session, user_id: UUID, external_id: int
) -> list[str]:
    """Distinct template keys of this feed's persisted signals — the accepted
    families to reseed when a verified feed is reopened (rule_id == template_key)."""
    statement = (
        select(ExtractedSignalRow.rule_id)
        .where(
            ExtractedSignalRow.user_id == user_id,
            ExtractedSignalRow.external_id == external_id,
            ExtractedSignalRow.rule_id.is_not(None),
        )
        .distinct()
    )
    return list(session.scalars(statement).all())


def _excluded_except(statement, row_type, keep: set[str]) -> dict:
    return {
        column.name: getattr(statement.excluded, column.name)
        for column in row_type.__table__.columns
        if column.name not in keep
    }


def record_outcome(session: Session, signal: ExtractedSignal, user_id: UUID) -> None:
    """Recompute one event's projection: upsert the extracted signal by
    (user_id, event_id). Re-recording the same extraction is a no-op change."""
    statement = pg_insert(ExtractedSignalRow).values(
        _with_user_id(_extracted_values(signal), user_id)
    )
    statement = statement.on_conflict_do_update(
        index_elements=["user_id", "event_id"],
        set_=_excluded_except(
            statement, ExtractedSignalRow, {"id", "user_id", "event_id"}
        ),
    )
    session.execute(statement)
