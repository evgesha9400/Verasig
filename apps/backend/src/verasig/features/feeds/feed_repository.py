"""Feed repository: the user-owned stream a user follows.

Merges the old channel repo (stream metadata + backfill cursor) and the old
subscription repo (membership) now that both live on one `feed` row.
Provider ids are stored as `external_id`; the domain `TelegramChannel` still
speaks `channel_id`, so this module is the translation boundary. Deleting a feed
cascades all of that user's capture + derived rows (FKs ON DELETE CASCADE), so a
re-add starts a fresh backfill from a NULL cursor.
"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
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
from verasig.domain.source import TELEGRAM
from verasig.features.feeds.history_depth import HistoryDepth
from verasig.features.sources import source_repository
from verasig.storage.models import FeedRow

logger = logging.getLogger(__name__)


def _metadata(channel: TelegramChannel) -> dict:
    return {
        "handle": channel.handle,
        "is_private": channel.is_private,
        "subscriber_count": channel.subscriber_count,
    }


def _require_source_id(session: Session, user_id: UUID) -> UUID:
    """The id of the user's source — every feed cascades from it (NOT NULL FK)."""
    source = source_repository.read_source(session, user_id, TELEGRAM)
    if source is None:
        raise ValueError(f"user {user_id} has no connected source to own the feed")
    return source.id


def _upsert_feed(
    session: Session,
    user_id: UUID,
    channel: TelegramChannel,
    added_at: datetime,
    *,
    reset_status: bool,
) -> FeedRow:
    """Insert the feed (membership + stream metadata) or refresh its metadata.

    On a fresh insert the cursor is NULL (a re-add backfills from the start).
    On conflict the cursor is never touched; `reset_status` re-arms a re-add to
    'new' but a metadata refresh mid-backfill leaves the status alone.
    """
    # Core insert against the table (not the ORM class): the column is literally
    # named "metadata", which collides with the declarative `Base.metadata` if
    # resolved as an ORM attribute in `set_`. Plain column-name keys avoid that.
    refreshed = {"title": channel.title, "metadata": _metadata(channel)}
    if reset_status:
        refreshed["status"] = "new"
    statement = pg_insert(FeedRow.__table__).values(
        user_id=user_id,
        external_id=channel.channel_id,
        source_id=_require_source_id(session, user_id),
        title=channel.title,
        status="new",
        captured_through_external_message_id=None,
        metadata=_metadata(channel),
        first_seen_at=channel.first_seen_at,
        added_at=added_at,
    )
    statement = statement.on_conflict_do_update(
        index_elements=["user_id", "external_id"],
        set_=refreshed,
    )
    session.execute(statement)
    session.flush()
    return read_feed(session, user_id, channel.channel_id)


def create_feed(
    session: Session, user_id: UUID, channel: TelegramChannel, added_at: datetime
) -> FeedRow:
    return _upsert_feed(session, user_id, channel, added_at, reset_status=True)


def upsert_feed_metadata(
    session: Session, user_id: UUID, channel: TelegramChannel, added_at: datetime
) -> FeedRow:
    return _upsert_feed(session, user_id, channel, added_at, reset_status=False)


def delete_feed(session: Session, user_id: UUID, external_id: int) -> None:
    logger.info(
        "delete_feed start: user=%s external_id=%s (cascade-deletes the feed and all "
        "of this user's captured messages, events, derived rows, and the backfill "
        "cursor)",
        user_id,
        external_id,
    )
    deleted = session.execute(
        delete(FeedRow).where(
            FeedRow.user_id == user_id, FeedRow.external_id == external_id
        )
    ).rowcount
    logger.info(
        "delete_feed done: user=%s external_id=%s removed=%s; re-adding refetches the "
        "full history from a NULL cursor",
        user_id,
        external_id,
        deleted,
    )


def read_feeds(session: Session, user_id: UUID) -> list[FeedRow]:
    return list(
        session.scalars(
            select(FeedRow).where(FeedRow.user_id == user_id).order_by(FeedRow.added_at)
        )
    )


def read_feed(session: Session, user_id: UUID, external_id: int) -> FeedRow | None:
    return session.get(FeedRow, (user_id, external_id))


def _row_to_channel(row: FeedRow) -> TelegramChannel:
    """Translate a stored feed back into the domain `TelegramChannel`."""
    return TelegramChannel(
        channel_id=row.external_id,
        handle=row.meta.get("handle"),
        title=row.title,
        is_private=row.meta.get("is_private", False),
        subscriber_count=row.meta.get("subscriber_count"),
        first_seen_at=row.first_seen_at,
        captured_through_message_id=row.captured_through_external_message_id,
    )


def read_feed_channel(
    session: Session, user_id: UUID, external_id: int
) -> TelegramChannel | None:
    row = read_feed(session, user_id, external_id)
    return _row_to_channel(row) if row else None


def set_status(
    session: Session, user_id: UUID, external_id: int, status: str
) -> FeedRow | None:
    row = read_feed(session, user_id, external_id)
    if row is None:
        return None
    row.status = status
    session.flush()
    return row


def read_history_depth(
    session: Session, user_id: UUID, external_id: int
) -> HistoryDepth:
    """The feed's chosen capture depth; defaults to one year when unknown."""
    row = read_feed(session, user_id, external_id)
    return HistoryDepth(row.history_depth) if row else HistoryDepth.ONE_YEAR


def set_history_depth(
    session: Session, user_id: UUID, external_id: int, depth: HistoryDepth
) -> FeedRow | None:
    row = read_feed(session, user_id, external_id)
    if row is None:
        return None
    row.history_depth = depth.value
    session.flush()
    return row


def count_feeds(session: Session, user_id: UUID) -> int:
    return session.scalar(
        select(func.count()).select_from(FeedRow).where(FeedRow.user_id == user_id)
    )


def read_cursor(session: Session, user_id: UUID, external_id: int) -> int | None:
    row = read_feed(session, user_id, external_id)
    return row.captured_through_external_message_id if row else None


def advance_cursor(
    session: Session, user_id: UUID, external_id: int, through_external_message_id: int
) -> None:
    row = read_feed(session, user_id, external_id)
    if row is None:  # feed deleted mid-backfill; nothing to advance (cf. reset_cursor)
        return
    if through_external_message_id > (row.captured_through_external_message_id or 0):
        row.captured_through_external_message_id = through_external_message_id


def reset_cursor(session: Session, user_id: UUID, external_id: int) -> None:
    row = read_feed(session, user_id, external_id)
    if row is not None:
        row.captured_through_external_message_id = None


def find_feed(session: Session, user_id: UUID, reference: str | int) -> FeedRow | None:
    parsed = parse_channel_reference(reference)
    if parsed.kind is ChannelReferenceKind.ID:
        return read_feed(session, user_id, int(parsed.value))
    if parsed.kind is ChannelReferenceKind.TITLE:
        return _find_feed_by_title(session, user_id, str(parsed.value))
    return _find_feed_by_handle(session, user_id, parsed)


def _find_feed_by_handle(
    session: Session, user_id: UUID, reference: ChannelReference
) -> FeedRow | None:
    handle = channel_lookup_handle(reference)
    if handle is None:
        return None
    return session.scalar(
        select(FeedRow).where(
            FeedRow.user_id == user_id,
            FeedRow.meta["handle"].astext == handle,
        )
    )


def _find_feed_by_title(session: Session, user_id: UUID, title: str) -> FeedRow | None:
    wanted = normalize_channel_title(title)
    rows = session.scalars(select(FeedRow).where(FeedRow.user_id == user_id)).all()
    matches = [row for row in rows if normalize_channel_title(row.title) == wanted]
    if len(matches) > 1:
        raise ChannelReferenceResolutionError(
            f"Found multiple feeds with title {title!r}; use numeric id."
        )
    return matches[0] if matches else None
