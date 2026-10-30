"""Resumable, chunked history backfill (spec §4.1, ADR 0014).

Resolve the channel, then stream messages NEWEST->OLDEST. Each batch is inserted
and advances the top cursor in one committed transaction, so a crash mid-stream
loses at most the in-flight batch and a restart resumes from the oldest captured
id — paging further into the past without refetching, because the capture insert
is ON CONFLICT DO NOTHING. `extend_newer` (REFRESH) instead pulls only messages
posted since the top cursor, OLDEST->NEWEST, so the committed top cursor only
ever advances over a contiguous range. Only one batch is ever held. Capture is
user-owned, so every step is scoped by `user_id`.
"""

import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from verasig.domain.message import RawTelegramMessage
from verasig.domain.telegram_ports import TelegramSource
from verasig.features.feeds import feed_repository, message_repository

logger = logging.getLogger(__name__)


class FeedDeletedError(RuntimeError):
    """The feed was deleted while its backfill job was in flight."""


@dataclass(frozen=True)
class BackfillResult:
    external_id: int
    inserted: int
    captured_through_external_message_id: int | None


async def backfill(
    source: TelegramSource,
    user_id: UUID,
    reference: str | int,
    session_factory: sessionmaker,
    batch_size: int,
    on_batch: Callable[[int, datetime], None] | None = None,
    since: datetime | None = None,
    extend_newer: bool = False,
    require_feed: bool = False,
) -> BackfillResult:
    """`require_feed` refuses to create a missing feed: a job started for an
    existing feed raises `FeedDeletedError` instead of re-creating a deleted one."""
    external_id = await _register_feed(
        source, user_id, reference, session_factory, require_feed
    )
    logger.info(
        "backfill stream: user=%s external_id=%s extend_newer=%s since=%s",
        user_id,
        external_id,
        extend_newer,
        since,
    )
    inserted = 0
    async for batch in _open_stream(
        source, session_factory, user_id, external_id, batch_size, since, extend_newer
    ):
        inserted += _persist_batch(session_factory, user_id, external_id, batch)
        if on_batch and batch:
            on_batch(inserted, min(message.posted_at for message in batch))
    final_cursor = _read_cursor(session_factory, user_id, external_id)
    logger.info(
        "backfill stream complete: user=%s external_id=%s inserted=%s cursor=%s",
        user_id,
        external_id,
        inserted,
        final_cursor,
    )
    return BackfillResult(external_id, inserted, final_cursor)


def _open_stream(
    source: TelegramSource,
    session_factory: sessionmaker,
    user_id: UUID,
    external_id: int,
    batch_size: int,
    since: datetime | None,
    extend_newer: bool,
) -> AsyncIterator[list[RawTelegramMessage]]:
    """REFRESH pulls messages newer than the top cursor; a capture (initial /
    resume / re-fetch) pages older than the oldest captured id, down to `since`."""
    if extend_newer:
        after = _read_cursor(session_factory, user_id, external_id)
        return source.fetch_newer_batches(external_id, after, batch_size)
    before = _read_oldest_captured_id(session_factory, user_id, external_id)
    return source.fetch_older_batches(external_id, before, batch_size, since=since)


async def _register_feed(
    source: TelegramSource,
    user_id: UUID,
    reference: str | int,
    session_factory: sessionmaker,
    require_feed: bool,
) -> int:
    channel = await source.resolve_channel(reference)
    with session_factory() as session:
        if not require_feed:
            feed_repository.upsert_feed_metadata(
                session, user_id, channel, datetime.now(tz=UTC)
            )
        elif feed_repository.refresh_feed_metadata(session, user_id, channel) is None:
            raise FeedDeletedError(f"feed {channel.channel_id} was deleted")
        session.commit()
        return channel.channel_id


def _persist_batch(
    session_factory: sessionmaker,
    user_id: UUID,
    external_id: int,
    batch: list[RawTelegramMessage],
) -> int:
    if not batch:
        return 0
    with session_factory() as session:
        inserted = message_repository.insert_messages(session, user_id, batch)
        feed_repository.advance_cursor(
            session, user_id, external_id, max(m.message_id for m in batch)
        )
        session.commit()
        return inserted


def _read_cursor(
    session_factory: sessionmaker, user_id: UUID, external_id: int
) -> int | None:
    with session_factory() as session:
        return feed_repository.read_cursor(session, user_id, external_id)


def _read_oldest_captured_id(
    session_factory: sessionmaker, user_id: UUID, external_id: int
) -> int | None:
    with session_factory() as session:
        return message_repository.read_oldest_message_id(session, user_id, external_id)
