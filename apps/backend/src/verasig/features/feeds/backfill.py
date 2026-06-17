"""Resumable, chunked history backfill (spec §4.1).

Resolve the channel, then stream `backfill_batches` oldest->newest. Each batch
is inserted and advances the cursor in **one committed transaction**, so a crash
mid-stream loses at most the in-flight batch and a restart resumes from the
persisted cursor without refetching captured ids. Only one batch is ever held.
Capture is user-owned, so every step is scoped by `user_id`.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from verasig.domain.message import RawTelegramMessage
from verasig.domain.telegram_ports import TelegramSource
from verasig.features.feeds import feed_repository, message_repository

logger = logging.getLogger(__name__)


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
) -> BackfillResult:
    external_id, cursor = await _register_feed(
        source, user_id, reference, session_factory
    )
    logger.info(
        "backfill stream: user=%s external_id=%s resuming after_message_id=%s "
        "(None means from the beginning)",
        user_id,
        external_id,
        cursor,
    )
    inserted = 0
    async for batch in source.backfill_batches(external_id, cursor, batch_size):
        inserted += _persist_batch(session_factory, user_id, external_id, batch)
        if on_batch and batch:
            on_batch(inserted, min(message.posted_at for message in batch))
    final_cursor = _read_cursor(session_factory, user_id, external_id)
    logger.info(
        "backfill stream complete: user=%s external_id=%s inserted=%s final_cursor=%s",
        user_id,
        external_id,
        inserted,
        final_cursor,
    )
    return BackfillResult(external_id, inserted, final_cursor)


async def _register_feed(
    source: TelegramSource,
    user_id: UUID,
    reference: str | int,
    session_factory: sessionmaker,
) -> tuple[int, int | None]:
    channel = await source.resolve_channel(reference)
    with session_factory() as session:
        feed_repository.upsert_feed_metadata(
            session, user_id, channel, datetime.now(tz=UTC)
        )
        session.commit()
        return channel.channel_id, feed_repository.read_cursor(
            session, user_id, channel.channel_id
        )


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
