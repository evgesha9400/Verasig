"""Re-fetch full history = verify reachability, then wipe & recapture (ADR 0014).

`BackfillMode.FULL` starts a new capture generation with a CLEAN wipe. It does
NOT secure deletion evidence — that is the deliberate, template-gated `Check gaps`
rescan (`deletion_rescan.py`), a separate operation. Before deleting anything the
wipe verifies the channel still resolves, so it never destroys a capture we could
not refill. What survives the wipe: durable `DeletedSignalEvidence` (ADR 0008) and
the backfill-run history — both FK to `feed`, not `raw_message`. The recapture
itself is the normal backfill stream that follows,
bounded by the feed's history depth.
"""

import logging
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from verasig.domain.telegram_ports import TelegramSource
from verasig.features.feeds import feed_repository, message_repository

logger = logging.getLogger(__name__)


class ChannelUnreachableError(RuntimeError):
    """The channel did not resolve — refusing to wipe a capture we cannot refill."""


async def guard_and_wipe(
    source: TelegramSource,
    user_id: UUID,
    external_id: int,
    session_factory: sessionmaker,
) -> int:
    """Verify the channel is reachable, then atomically wipe the feed's capture.

    Raises `ChannelUnreachableError` BEFORE any deletion if the channel does not
    resolve, so a wipe never runs against a channel the recapture could not refill.
    Returns the number of captured messages removed.
    """
    await _guard_reachable(source, external_id)
    messages_deleted = _wipe_capture(session_factory, user_id, external_id)
    logger.info(
        "recapture.guard_and_wipe done: external_id=%s messages_deleted=%s "
        "(rules + evidence + run history retained)",
        external_id,
        messages_deleted,
    )
    return messages_deleted


async def _guard_reachable(source: TelegramSource, external_id: int) -> None:
    try:
        await source.resolve_channel(external_id)
    except Exception as error:
        raise ChannelUnreachableError(
            f"feed {external_id}: channel did not resolve — refusing to wipe a "
            "capture we cannot refill"
        ) from error


def _wipe_capture(
    session_factory: sessionmaker, user_id: UUID, external_id: int
) -> int:
    with session_factory() as session:
        deleted = message_repository.delete_feed_messages(session, user_id, external_id)
        feed_repository.reset_cursor(session, user_id, external_id)
        feed_repository.advance_capture_generation(session, user_id, external_id)
        session.commit()
        return deleted
