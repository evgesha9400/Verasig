"""Queue-first live ingestion (ADR 0004).

Each delivered message is committed immediately. The raw-message composite key
dedupes push, poll, catch-up, and any rows captured by earlier backfill.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from statistics import median
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.message import DeliveryMode
from verasig.domain.telegram import (
    TelegramDeletionEvent,
    TelegramDeliveryEvent,
    TelegramLiveEvent,
)
from verasig.domain.telegram_ports import TelegramSource
from verasig.features.feeds import (
    deletion_repository,
    message_repository,
)


@dataclass(frozen=True)
class LiveIngestionResult:
    channel_ids: list[int]
    inserted: int
    duplicates: int
    deleted: int
    median_latency: timedelta | None
    captured_by_mode: dict[DeliveryMode, int]


@dataclass
class _LiveIngestionTally:
    inserted: int = 0
    duplicates: int = 0
    deleted: int = 0
    latencies: list[timedelta] = field(default_factory=list)
    captured_by_mode: dict[DeliveryMode, int] = field(default_factory=dict)


async def ingest_live(
    source: TelegramSource,
    user_id: UUID,
    channel_ids: list[int],
    session_factory: sessionmaker,
) -> LiveIngestionResult:
    tally = _LiveIngestionTally()
    async for event in source.live_events(channel_ids):
        _persist_event(session_factory, user_id, tally, event)
    return LiveIngestionResult(
        channel_ids=channel_ids,
        inserted=tally.inserted,
        duplicates=tally.duplicates,
        deleted=tally.deleted,
        median_latency=_median_latency(tally.latencies),
        captured_by_mode=tally.captured_by_mode,
    )


def _persist_event(
    session_factory: sessionmaker,
    user_id: UUID,
    tally: _LiveIngestionTally,
    event: TelegramLiveEvent,
) -> None:
    if isinstance(event, TelegramDeliveryEvent):
        inserted = _persist_delivery(session_factory, user_id, event)
        _record_delivery(tally, event, inserted)
        return
    written = _persist_deletion(session_factory, user_id, event)
    tally.deleted += written


def _persist_delivery(
    session_factory: sessionmaker, user_id: UUID, event: TelegramDeliveryEvent
) -> bool:
    with session_factory() as session:
        inserted = message_repository.insert_messages(session, user_id, [event.message])
        session.commit()
        return inserted == 1


def _record_delivery(
    tally: _LiveIngestionTally, event: TelegramDeliveryEvent, inserted: bool
) -> None:
    if not inserted:
        tally.duplicates += 1
        return
    tally.inserted += 1
    tally.latencies.append(event.captured_at - event.message.posted_at)
    mode = event.mode
    tally.captured_by_mode[mode] = tally.captured_by_mode.get(mode, 0) + 1


def _median_latency(latencies: list[timedelta]) -> timedelta | None:
    if not latencies:
        return None
    seconds = median(latency.total_seconds() for latency in latencies)
    return timedelta(seconds=seconds)


def _persist_deletion(
    session_factory: sessionmaker, user_id: UUID, event: TelegramDeletionEvent
) -> int:
    with session_factory() as session:
        message = message_repository.read_message(
            session, user_id, event.channel_id, event.message_id
        )
        was_candidate = message_repository.is_candidate_message(
            session, user_id, event.channel_id, event.message_id
        )
        evidence = _live_deletion_evidence(event, message, was_candidate)
        written = deletion_repository.upsert_deletion_evidence(
            session, user_id, [evidence]
        )
        session.commit()
        return written


def _live_deletion_evidence(
    event: TelegramDeletionEvent,
    message,
    was_signal_candidate: bool,
) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        channel_id=event.channel_id,
        message_id=event.message_id,
        confidence=DeletionConfidence.CONFIRMED,
        method=DeletionMethod.LIVE_EVENT,
        original_text=None if message is None else message.text,
        first_seen_at=None if message is None else message.captured_at,
        detected_at=event.detected_at,
        was_signal_candidate=was_signal_candidate,
    )
