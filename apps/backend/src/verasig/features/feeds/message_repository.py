"""Message repository functions.

The domain `RawTelegramMessage` speaks `channel_id`/`message_id`; storage speaks
`external_id`/`external_message_id` and is user-owned, so every read/write here
translates and is scoped by `user_id`.
"""

from uuid import UUID

from sqlalchemy import delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.message import RawTelegramMessage
from verasig.storage.models import RawMessageRow, SignalRow


def _message_values(user_id: UUID, message: RawTelegramMessage) -> dict:
    return {
        "user_id": user_id,
        "external_id": message.channel_id,
        "external_message_id": message.message_id,
        "text": message.text,
        "sender_id": message.sender_id,
        "posted_at": message.posted_at,
        "captured_at": message.captured_at,
        "reply_to_external_message_id": message.reply_to_message_id,
        "edit_date": message.edit_date,
        "has_media": message.has_media,
        "views": message.views,
        "forwards": message.forwards,
        "raw_payload": message.raw_payload,
    }


def insert_messages(
    session: Session, user_id: UUID, messages: list[RawTelegramMessage]
) -> int:
    if not messages:
        return 0
    statement = (
        pg_insert(RawMessageRow)
        .values([_message_values(user_id, message) for message in messages])
        .on_conflict_do_nothing(
            index_elements=[
                RawMessageRow.user_id,
                RawMessageRow.external_id,
                RawMessageRow.external_message_id,
            ]
        )
        .returning(RawMessageRow.external_message_id)
    )
    return len(session.execute(statement).fetchall())


def delete_feed_messages(session: Session, user_id: UUID, external_id: int) -> int:
    """Delete a feed's whole capture. Derived rows (signal events, extractions,
    lifecycle links) cascade from `raw_message`; durable deletion evidence FK to
    `feed`, so it survives (ADR 0014)."""
    return session.execute(
        delete(RawMessageRow).where(
            RawMessageRow.user_id == user_id,
            RawMessageRow.external_id == external_id,
        )
    ).rowcount


def count_messages(session: Session, user_id: UUID, external_id: int) -> int:
    return session.scalar(
        select(func.count())
        .select_from(RawMessageRow)
        .where(
            RawMessageRow.user_id == user_id,
            RawMessageRow.external_id == external_id,
        )
    )


def read_oldest_message_id(
    session: Session, user_id: UUID, external_id: int
) -> int | None:
    """The lowest captured message id — the back frontier a newest->oldest
    capture pages below to resume going further into the past. `None` when the
    feed has no capture yet (start from the newest message)."""
    return session.scalar(
        select(func.min(RawMessageRow.external_message_id)).where(
            RawMessageRow.user_id == user_id,
            RawMessageRow.external_id == external_id,
        )
    )


def _row_to_message(row: RawMessageRow) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=row.external_id,
        message_id=row.external_message_id,
        text=row.text,
        sender_id=row.sender_id,
        posted_at=row.posted_at,
        captured_at=row.captured_at,
        reply_to_message_id=row.reply_to_external_message_id,
        edit_date=row.edit_date,
        has_media=row.has_media,
        views=row.views,
        forwards=row.forwards,
        raw_payload=row.raw_payload,
    )


def read_message(
    session: Session, user_id: UUID, external_id: int, external_message_id: int
) -> RawTelegramMessage | None:
    row = session.get(RawMessageRow, (user_id, external_id, external_message_id))
    if row is None:
        return None
    return _row_to_message(row)


def read_messages(
    session: Session, user_id: UUID, external_id: int
) -> list[RawTelegramMessage]:
    rows = session.scalars(
        select(RawMessageRow)
        .where(
            RawMessageRow.user_id == user_id,
            RawMessageRow.external_id == external_id,
        )
        .order_by(RawMessageRow.external_message_id)
    ).all()
    return [_row_to_message(row) for row in rows]


def read_message_page(
    session: Session,
    user_id: UUID,
    external_id: int,
    after_external_message_id: int,
    limit: int,
) -> list[RawTelegramMessage]:
    """One bounded page of messages with id > cursor (keyset pagination)."""
    rows = session.scalars(
        select(RawMessageRow)
        .where(
            RawMessageRow.user_id == user_id,
            RawMessageRow.external_id == external_id,
            RawMessageRow.external_message_id > after_external_message_id,
        )
        .order_by(RawMessageRow.external_message_id)
        .limit(limit)
    ).all()
    return [_row_to_message(row) for row in rows]


def is_candidate_message(
    session: Session, user_id: UUID, external_id: int, message_id: int
) -> bool:
    """Whether one message yielded a persisted signal — a single EXISTS instead
    of scanning every candidate id just to classify one deletion."""
    return bool(
        session.scalar(
            select(
                exists().where(
                    SignalRow.user_id == user_id,
                    SignalRow.external_id == external_id,
                    SignalRow.external_message_id == message_id,
                )
            )
        )
    )


def candidate_message_ids(
    session: Session, user_id: UUID, external_id: int
) -> set[int]:
    return set(
        session.scalars(
            select(SignalRow.external_message_id).where(
                SignalRow.user_id == user_id,
                SignalRow.external_id == external_id,
            )
        ).all()
    )
