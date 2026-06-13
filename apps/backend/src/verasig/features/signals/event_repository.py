"""Event repository functions."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.event import RawSignalEvent
from verasig.storage.models import RawSignalEventRow


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
