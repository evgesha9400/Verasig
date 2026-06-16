"""Gated deletion rescan (ADR 0008).

Re-fetch the channel's CURRENT live message-id set, diff it against the durable
stored set, and persist the evidence. The channel must already be backfilled
(stored messages are the left side of the diff), so it is resolved from the DB,
never from the source. An empty/failed live re-fetch ABORTS — an inaccessible
channel must never be read as a mass deletion. Mirrors `backfill.py`: a pure
core (`detect_deletions`) wrapped in repo-driven orchestration; `live_message_ids`
never runs against real Telegram in tests.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import sessionmaker

from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
)
from verasig.domain.telegram_ports import TelegramSource
from verasig.features.sources import (
    channel_repository,
    deletion_repository,
    message_repository,
)
from verasig.features.sources.deletion_diff import detect_deletions

logger = logging.getLogger(__name__)


class RescanAborted(RuntimeError):
    """The live re-fetch was empty/failed — refusing to read it as a deletion."""


@dataclass(frozen=True)
class RescanResult:
    channel_id: int
    confirmed: int  # CONFIRMED deletions detected this rescan
    suspected: int  # SUSPECTED gaps detected this rescan
    written: int  # rows newly written/upgraded (0 on a same-state re-run)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


async def rescan(
    source: TelegramSource,
    reference: str | int,
    session_factory: sessionmaker,
    on_progress: Callable[[int], None] | None = None,
) -> RescanResult:
    channel_id = _resolve_channel_id(session_factory, reference)
    logger.info(
        "rescan.live_message_ids begin: channel=%s (walking the full live channel "
        "via the source — may take a while for large channels)",
        channel_id,
    )
    live_ids = await source.live_message_ids(channel_id, on_progress=on_progress)
    logger.info(
        "rescan.live_message_ids done: channel=%s live_count=%s",
        channel_id,
        len(live_ids),
    )
    _guard_live_snapshot(live_ids, channel_id)
    evidence = _detect(session_factory, channel_id, live_ids)
    written = _persist(session_factory, evidence)
    return _tally(channel_id, evidence, written)


def _resolve_channel_id(session_factory: sessionmaker, reference: str | int) -> int:
    with session_factory() as session:
        channel = channel_repository.find_channel(session, reference)
    if channel is None:
        raise ValueError(f"no channel matching {reference!r}; run backfill first")
    return channel.channel_id


def _guard_live_snapshot(live_ids: set[int], channel_id: int) -> None:
    if not live_ids:
        raise RescanAborted(
            f"channel {channel_id}: empty live snapshot — refusing to read an "
            "inaccessible channel as a mass deletion"
        )


def _detect(
    session_factory: sessionmaker, channel_id: int, live_ids: set[int]
) -> list[DeletedSignalEvidence]:
    with session_factory() as session:
        stored = message_repository.read_messages(session, channel_id)
        candidates = message_repository.candidate_message_ids(session, channel_id)
    return detect_deletions(channel_id, stored, live_ids, candidates, _utc_now())


def _persist(
    session_factory: sessionmaker, evidence: list[DeletedSignalEvidence]
) -> int:
    with session_factory() as session:
        written = deletion_repository.upsert_deletion_evidence(session, evidence)
        session.commit()
        return written


def _tally(
    channel_id: int, evidence: list[DeletedSignalEvidence], written: int
) -> RescanResult:
    confirmed = sum(
        1 for item in evidence if item.confidence is DeletionConfidence.CONFIRMED
    )
    return RescanResult(channel_id, confirmed, len(evidence) - confirmed, written)
