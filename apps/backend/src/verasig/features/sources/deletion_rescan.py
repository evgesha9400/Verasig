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
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
)
from verasig.domain.telegram_ports import TelegramSource
from verasig.features.sources import (
    deletion_repository,
    feed_repository,
    message_repository,
)
from verasig.features.sources.deletion_diff import detect_deletions

logger = logging.getLogger(__name__)


class RescanAborted(RuntimeError):
    """The live re-fetch was empty/failed — refusing to read it as a deletion."""


@dataclass(frozen=True)
class RescanResult:
    external_id: int
    confirmed: int  # CONFIRMED deletions detected this rescan
    suspected: int  # SUSPECTED gaps detected this rescan
    written: int  # rows newly written/upgraded (0 on a same-state re-run)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


async def rescan(
    source: TelegramSource,
    user_id: UUID,
    reference: str | int,
    session_factory: sessionmaker,
    on_progress: Callable[[int], None] | None = None,
) -> RescanResult:
    external_id = _resolve_external_id(session_factory, user_id, reference)
    logger.info(
        "rescan.live_message_ids begin: external_id=%s (walking the full live channel "
        "via the source — may take a while for large channels)",
        external_id,
    )
    live_ids = await source.live_message_ids(external_id, on_progress=on_progress)
    logger.info(
        "rescan.live_message_ids done: external_id=%s live_count=%s",
        external_id,
        len(live_ids),
    )
    _guard_live_snapshot(live_ids, external_id)
    evidence = _detect(session_factory, user_id, external_id, live_ids)
    written = _persist(session_factory, user_id, evidence)
    return _tally(external_id, evidence, written)


def _resolve_external_id(
    session_factory: sessionmaker, user_id: UUID, reference: str | int
) -> int:
    with session_factory() as session:
        feed = feed_repository.find_feed(session, user_id, reference)
    if feed is None:
        raise ValueError(f"no feed matching {reference!r}; run backfill first")
    return feed.external_id


def _guard_live_snapshot(live_ids: set[int], external_id: int) -> None:
    if not live_ids:
        raise RescanAborted(
            f"feed {external_id}: empty live snapshot — refusing to read an "
            "inaccessible channel as a mass deletion"
        )


def _detect(
    session_factory: sessionmaker,
    user_id: UUID,
    external_id: int,
    live_ids: set[int],
) -> list[DeletedSignalEvidence]:
    with session_factory() as session:
        stored = message_repository.read_messages(session, user_id, external_id)
        candidates = message_repository.candidate_message_ids(
            session, user_id, external_id
        )
    return detect_deletions(external_id, stored, live_ids, candidates, _utc_now())


def _persist(
    session_factory: sessionmaker,
    user_id: UUID,
    evidence: list[DeletedSignalEvidence],
) -> int:
    with session_factory() as session:
        written = deletion_repository.upsert_deletion_evidence(
            session, user_id, evidence
        )
        session.commit()
        return written


def _tally(
    external_id: int, evidence: list[DeletedSignalEvidence], written: int
) -> RescanResult:
    confirmed = sum(
        1 for item in evidence if item.confidence is DeletionConfidence.CONFIRMED
    )
    return RescanResult(external_id, confirmed, len(evidence) - confirmed, written)
