"""Resumable, chunked history backfill (spec §4.1).

Resolve the channel, then stream `backfill_batches` oldest->newest. Each batch
is inserted and advances the cursor in **one committed transaction**, so a crash
mid-stream loses at most the in-flight batch and a restart resumes from the
persisted cursor without refetching captured ids. Only one batch is ever held.
"""

from dataclasses import dataclass

from sqlalchemy.orm import sessionmaker

from verasig.domain.message import RawTelegramMessage
from verasig.domain.protocols import TelegramSource
from verasig.storage import repositories as repo


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
) -> BackfillResult:
    channel_id, cursor = await _register_channel(source, reference, session_factory)
    inserted = 0
    async for batch in source.backfill_batches(channel_id, cursor, batch_size):
        inserted += _persist_batch(session_factory, channel_id, batch)
    final_cursor = _read_cursor(session_factory, channel_id)
    return BackfillResult(channel_id, inserted, final_cursor)


async def _register_channel(
    source: TelegramSource, reference: str | int, session_factory: sessionmaker
) -> tuple[int, int | None]:
    channel = await source.resolve_channel(reference)
    with session_factory() as session:
        repo.upsert_channel(session, channel)
        session.commit()
        return channel.channel_id, repo.read_cursor(session, channel.channel_id)


def _persist_batch(
    session_factory: sessionmaker, channel_id: int, batch: list[RawTelegramMessage]
) -> int:
    if not batch:
        return 0
    with session_factory() as session:
        inserted = repo.insert_messages(session, batch)
        repo.advance_cursor(session, channel_id, max(m.message_id for m in batch))
        session.commit()
        return inserted


def _read_cursor(session_factory: sessionmaker, channel_id: int) -> int | None:
    with session_factory() as session:
        return repo.read_cursor(session, channel_id)
