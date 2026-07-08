"""Mining Confirm: persist the accepted template families' signals (ADR 0015).

Confirm is the operator accepting the reviewed template families. The backend
owns extraction end-to-end via the ported miner: it re-mines the feed's stored
messages (byte-identical port, so the ``template_key``s match what the client
reviewed), keeps the accepted families, and persists each candidate as one
``Signal`` — the row the Signals view reads — then marks the feed ``verified``.

Persistence is a REPLACE of the feed's whole signal projection: one transaction
deletes every ``signal`` row for (user, channel), then inserts the accepted
candidates' signals. This is simpler than an event-upsert + re-resolve dance,
and it fixes a real bug: confirming a SMALLER accepted set than a prior confirm
used to leave the de-selected families' signals orphaned (they resurrected on
reopen) because nothing ever deleted them. A replace makes the persisted set
always exactly the accepted set.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from verasig.domain.feed import FeedStatus
from verasig.domain.signal import Signal
from verasig.features.feeds import feed_repository, message_repository
from verasig.features.mining.mining_signals import candidate_to_signal
from verasig.features.mining.template_mining import mine_template_groups
from verasig.features.mining.template_mining.types import ChatMessage, TemplateGroup
from verasig.features.parser_overlay.repository import read_overlay
from verasig.features.signals import outcome_repository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MiningConfirmResult:
    feed_status: str
    templates_accepted: int
    signals_extracted: int


def confirm_mined_signals(
    session_factory: sessionmaker,
    user_id: UUID,
    external_id: int,
    accepted_template_keys: Sequence[str],
) -> MiningConfirmResult:
    accepted = set(accepted_template_keys)
    _messages, groups, _overlay = mine_feed_messages(
        session_factory, user_id, external_id
    )
    kept = [group for group in groups if group.template_key in accepted]
    signals = _signals_of(kept, external_id)
    extracted = _replace_feed_signals(session_factory, user_id, external_id, signals)
    status = _mark_verified(session_factory, user_id, external_id)
    logger.info(
        "mining.confirm done: external_id=%s templates=%s signals=%s status=%s",
        external_id,
        len(kept),
        extracted,
        status,
    )
    return MiningConfirmResult(
        feed_status=status,
        templates_accepted=len(kept),
        signals_extracted=extracted,
    )


def read_confirmed_template_keys(
    session_factory: sessionmaker, user_id: UUID, external_id: int
) -> list[str]:
    """The accepted template keys recovered from persisted signals — the resume
    source for the Verify audit when a verified feed is reopened."""
    with session_factory() as session:
        return outcome_repository.read_confirmed_template_keys(
            session, user_id, external_id
        )


def mine_feed_messages(
    session_factory: sessionmaker, user_id: UUID, external_id: int
) -> tuple[list[ChatMessage], list[TemplateGroup], dict]:
    """Re-mine a feed's stored messages (byte-identical port, so the
    ``template_key``s match what the client reviewed). Shared by confirm and the
    Verify audit — both need the SAME re-mine of the SAME stored history, and the
    same overlay the mine ran with."""
    with session_factory() as session:
        messages = message_repository.read_messages(session, user_id, external_id)
        overlay = read_overlay(session, user_id)
    chat_messages = [_to_chat_message(message) for message in messages]
    return chat_messages, mine_template_groups(chat_messages, overlay), overlay


def _to_chat_message(message) -> ChatMessage:
    return ChatMessage(
        id=str(message.message_id),
        text=message.text or "",
        date=message.posted_at.isoformat() if message.posted_at else None,
    )


def _signals_of(groups: Sequence[TemplateGroup], external_id: int) -> list[Signal]:
    return [
        signal
        for group in groups
        for candidate in group.candidates
        if (signal := candidate_to_signal(candidate, external_id)) is not None
    ]


def _replace_feed_signals(
    session_factory: sessionmaker,
    user_id: UUID,
    external_id: int,
    signals: Sequence[Signal],
) -> int:
    """Atomically rewrite the feed's signal projection: delete every stored
    signal for this feed, then insert exactly the accepted candidates' — so a
    smaller reconfirm actually removes the de-selected families."""
    with session_factory() as session:
        outcome_repository.delete_signals_for_channel(session, user_id, external_id)
        extracted = outcome_repository.insert_signals(session, list(signals), user_id)
        session.commit()
        return extracted


def _mark_verified(
    session_factory: sessionmaker, user_id: UUID, external_id: int
) -> str:
    with session_factory() as session:
        feed_repository.set_status(session, user_id, external_id, FeedStatus.VERIFIED)
        session.commit()
    return FeedStatus.VERIFIED
