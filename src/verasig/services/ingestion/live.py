"""Queue-first live ingestion (Slice 10; ADR 0004).

Each delivered message is committed immediately. The raw-message composite key
dedupes push, poll, catch-up, and any rows captured by earlier backfill.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import sessionmaker

from verasig.domain.message import DeliveryMode
from verasig.foundation.telegram_source import TelegramDeliveryEvent, TelegramSource
from verasig.storage import repositories as repo


@dataclass(frozen=True)
class LiveIngestionResult:
    channel_ids: list[int]
    inserted: int
    duplicates: int
    captured_by_mode: dict[DeliveryMode, int]


@dataclass
class _LiveIngestionTally:
    inserted: int = 0
    duplicates: int = 0
    captured_by_mode: dict[DeliveryMode, int] = field(default_factory=dict)


async def ingest_live(
    source: TelegramSource,
    channel_ids: list[int],
    session_factory: sessionmaker,
) -> LiveIngestionResult:
    tally = _LiveIngestionTally()
    async for event in source.live_events(channel_ids):
        inserted = _persist_delivery(session_factory, event)
        _record_delivery(tally, event.mode, inserted)
    return LiveIngestionResult(
        channel_ids=channel_ids,
        inserted=tally.inserted,
        duplicates=tally.duplicates,
        captured_by_mode=tally.captured_by_mode,
    )


def _persist_delivery(
    session_factory: sessionmaker, event: TelegramDeliveryEvent
) -> bool:
    with session_factory() as session:
        inserted = repo.insert_messages(session, [event.message])
        session.commit()
        return inserted == 1


def _record_delivery(
    tally: _LiveIngestionTally, mode: DeliveryMode, inserted: bool
) -> None:
    if not inserted:
        tally.duplicates += 1
        return
    tally.inserted += 1
    tally.captured_by_mode[mode] = tally.captured_by_mode.get(mode, 0) + 1
