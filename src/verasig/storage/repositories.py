"""Insert-only repositories for raw capture (Slice 2).

Messages are appended with `ON CONFLICT DO NOTHING` (idempotent on the
`(channel_id, message_id)` PK). The channel row is upserted for metadata, but
its `first_seen_at` and the `captured_through_message_id` cursor are preserved
across re-resolves — only the cursor's own monotonic advance moves it.
"""

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage
from verasig.storage.models import ChannelRow, RawMessageRow


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
