"""Re-fetch full history = secure evidence, then wipe & recapture (ADR 0014).

`BackfillMode.FULL` starts a new capture generation. Append-only capture (ADR
0001) still holds *within* a generation; a FULL re-fetch first secures deletion
evidence (a mandatory pre-wipe `Rescan`, which aborts on an empty live snapshot
so an inaccessible channel is never read as a mass deletion), then atomically
deletes the feed's capture and cascaded derived rows and clears the cursor. What
survives: durable `DeletedSignalEvidence` (ADR 0008), distilled rules, and the
backfill-run history — all FK to `feed`, not `raw_message`. The recapture itself
is the normal backfill stream that follows, bounded by the feed's history depth.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from verasig.domain.telegram_ports import TelegramSource
from verasig.features.feeds import feed_repository, message_repository
from verasig.features.feeds.deletion_rescan import rescan

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WipeResult:
    evidence_written: int  # deletion-evidence rows secured before the wipe
    messages_deleted: int  # captured messages removed (derived rows cascade)


async def secure_and_wipe(
    source: TelegramSource,
    user_id: UUID,
    external_id: int,
    session_factory: sessionmaker,
    on_progress: Callable[[int], None] | None = None,
) -> WipeResult:
    """Secure deletion evidence, then atomically wipe the feed's capture.

    Raises `RescanAborted` (from `rescan`) BEFORE any deletion if the live
    snapshot is empty, so a wipe never runs against an inaccessible channel.
    """
    evidence_written = await _secure_evidence(
        source, user_id, external_id, session_factory, on_progress
    )
    messages_deleted = _wipe_capture(session_factory, user_id, external_id)
    logger.info(
        "recapture.secure_and_wipe done: external_id=%s evidence_written=%s "
        "messages_deleted=%s (rules + evidence + run history retained)",
        external_id,
        evidence_written,
        messages_deleted,
    )
    return WipeResult(evidence_written, messages_deleted)


async def _secure_evidence(
    source: TelegramSource,
    user_id: UUID,
    external_id: int,
    session_factory: sessionmaker,
    on_progress: Callable[[int], None] | None,
) -> int:
    result = await rescan(
        source, user_id, external_id, session_factory, on_progress=on_progress
    )
    return result.written


def _wipe_capture(
    session_factory: sessionmaker, user_id: UUID, external_id: int
) -> int:
    with session_factory() as session:
        deleted = message_repository.delete_feed_messages(session, user_id, external_id)
        feed_repository.reset_cursor(session, user_id, external_id)
        session.commit()
        return deleted
