"""Channel repository functions."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.channel import TelegramChannel
from verasig.domain.channel_reference import (
    ChannelReference,
    ChannelReferenceKind,
    ChannelReferenceResolutionError,
    channel_lookup_handle,
    normalize_channel_title,
    parse_channel_reference,
)
from verasig.storage.models import ChannelRow


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


def advance_cursor(session: Session, channel_id: int, through_message_id: int) -> None:
    channel = session.get(ChannelRow, channel_id)
    if through_message_id > (channel.captured_through_message_id or 0):
        channel.captured_through_message_id = through_message_id


def reset_cursor(session: Session, channel_id: int) -> None:
    channel = session.get(ChannelRow, channel_id)
    if channel is not None:
        channel.captured_through_message_id = None


def read_cursor(session: Session, channel_id: int) -> int | None:
    channel = session.get(ChannelRow, channel_id)
    return channel.captured_through_message_id if channel else None


def find_channel(session: Session, reference: str | int) -> ChannelRow | None:
    parsed = parse_channel_reference(reference)
    if parsed.kind is ChannelReferenceKind.ID:
        return session.get(ChannelRow, int(parsed.value))
    if parsed.kind is ChannelReferenceKind.TITLE:
        return _find_channel_by_title(session, str(parsed.value))
    return _find_channel_by_handle(session, parsed)


def _find_channel_by_handle(
    session: Session, reference: ChannelReference
) -> ChannelRow | None:
    handle = channel_lookup_handle(reference)
    if handle is None:
        return None
    return session.scalar(select(ChannelRow).where(ChannelRow.handle == handle))


def _find_channel_by_title(session: Session, title: str) -> ChannelRow | None:
    wanted = normalize_channel_title(title)
    rows = session.scalars(select(ChannelRow)).all()
    matches = [row for row in rows if normalize_channel_title(row.title) == wanted]
    if len(matches) > 1:
        raise ChannelReferenceResolutionError(
            f"Found multiple captured channels with title {title!r}; use numeric id."
        )
    return matches[0] if matches else None
