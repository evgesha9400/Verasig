"""Message repository functions."""

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.message import RawTelegramMessage
from verasig.storage.models import RawMessageRow, RawSignalEventRow


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


def count_messages(session: Session, channel_id: int) -> int:
    return session.scalar(
        select(func.count())
        .select_from(RawMessageRow)
        .where(RawMessageRow.channel_id == channel_id)
    )


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
