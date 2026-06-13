"""Drift repository functions."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.drift import FilterDriftWarning, ParserDriftWarning
from verasig.storage.models import FilterDriftWarningRow, ParserDriftWarningRow


def insert_drift_warnings(
    session: Session, warnings: list[FilterDriftWarning], user_id: UUID
) -> int:
    if not warnings:
        return 0
    statement = (
        pg_insert(FilterDriftWarningRow)
        .values(
            [
                {
                    "id": warning.id,
                    "user_id": user_id,
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
        .on_conflict_do_nothing(index_elements=["user_id", "channel_id", "message_id"])
        .returning(FilterDriftWarningRow.id)
    )
    return len(session.execute(statement).fetchall())


def read_drift_warnings(
    session: Session, channel_id: int, user_id: UUID
) -> list[FilterDriftWarning]:
    rows = session.scalars(
        select(FilterDriftWarningRow).where(
            FilterDriftWarningRow.channel_id == channel_id,
            FilterDriftWarningRow.user_id == user_id,
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


def read_parser_drift_warnings(
    session: Session, channel_id: int, user_id: UUID
) -> list[ParserDriftWarning]:
    rows = session.scalars(
        select(ParserDriftWarningRow).where(
            ParserDriftWarningRow.channel_id == channel_id,
            ParserDriftWarningRow.user_id == user_id,
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
