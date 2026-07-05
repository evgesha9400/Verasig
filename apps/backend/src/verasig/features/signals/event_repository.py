"""Event repository functions.

The domain `RawSignalEvent` speaks `channel_id`/`message_id`; storage speaks
`external_id`/`external_message_id` and is user-owned.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.event import RawSignalEvent
from verasig.storage.models import RawSignalEventRow


def insert_signal_events(
    session: Session, user_id: UUID, events: list[RawSignalEvent]
) -> int:
    if not events:
        return 0
    statement = (
        pg_insert(RawSignalEventRow)
        .values(
            [
                {
                    "id": event.id,
                    "user_id": user_id,
                    "external_id": event.channel_id,
                    "external_message_id": event.message_id,
                    "candidate_text": event.candidate_text,
                    "materialized_by": event.materialized_by.value,
                    "matched_reasons": [
                        reason.value for reason in event.matched_reasons
                    ],
                    "created_at": event.created_at,
                }
                for event in events
            ]
        )
        .on_conflict_do_nothing(
            index_elements=["user_id", "external_id", "external_message_id"]
        )
        .returning(RawSignalEventRow.id)
    )
    return len(session.execute(statement).fetchall())


def read_signal_events(
    session: Session, user_id: UUID, external_id: int
) -> list[RawSignalEvent]:
    rows = session.scalars(
        select(RawSignalEventRow).where(
            RawSignalEventRow.user_id == user_id,
            RawSignalEventRow.external_id == external_id,
        )
    ).all()
    return [
        RawSignalEvent(
            id=row.id,
            channel_id=row.external_id,
            message_id=row.external_message_id,
            candidate_text=row.candidate_text,
            materialized_by=row.materialized_by,
            matched_reasons=row.matched_reasons,
            created_at=row.created_at,
        )
        for row in rows
    ]
