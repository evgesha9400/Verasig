"""Resumable, chunked history backfill (spec §4.1).

Resolve the channel, then stream `backfill_batches` oldest->newest. Each batch
is inserted and advances the cursor in **one committed transaction**, so a crash
mid-stream loses at most the in-flight batch and a restart resumes from the
persisted cursor without refetching captured ids. Only one batch is ever held.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import sessionmaker

from verasig.domain.message import RawTelegramMessage
from verasig.domain.telegram_ports import TelegramSource
from verasig.features.sources import (
    channel_repository,
    message_repository,
)


@dataclass(frozen=True)
class BackfillResult:
    channel_id: int
    inserted: int
    captured_through_message_id: int | None


async def backfill(
    source: TelegramSource,
    reference: str | int,
    session_factory: sessionmaker,
    batch_size: int,
    on_batch: Callable[[int, datetime], None] | None = None,
) -> BackfillResult:
    channel_id, cursor = await _register_channel(source, reference, session_factory)
    inserted = 0
    async for batch in source.backfill_batches(channel_id, cursor, batch_size):
        inserted += _persist_batch(session_factory, channel_id, batch)
        if on_batch and batch:
            on_batch(inserted, min(message.posted_at for message in batch))
    final_cursor = _read_cursor(session_factory, channel_id)
    return BackfillResult(channel_id, inserted, final_cursor)


async def _register_channel(
    source: TelegramSource, reference: str | int, session_factory: sessionmaker
) -> tuple[int, int | None]:
    channel = await source.resolve_channel(reference)
    with session_factory() as session:
        channel_repository.upsert_channel(session, channel)
        session.commit()
        return channel.channel_id, channel_repository.read_cursor(
            session, channel.channel_id
        )


def _persist_batch(
    session_factory: sessionmaker, channel_id: int, batch: list[RawTelegramMessage]
) -> int:
    if not batch:
        return 0
    with session_factory() as session:
        inserted = message_repository.insert_messages(session, batch)
        channel_repository.advance_cursor(
            session, channel_id, max(m.message_id for m in batch)
        )
        session.commit()
        return inserted


def _read_cursor(session_factory: sessionmaker, channel_id: int) -> int | None:
    with session_factory() as session:
        return channel_repository.read_cursor(session, channel_id)
