"""Mining Confirm: persist the accepted template families' signals (ADR 0015).

Confirm is the operator accepting the reviewed template families. The backend
owns extraction end-to-end via the ported miner: it re-mines the feed's stored
messages (byte-identical port, so the ``template_key``s match what the client
reviewed), keeps the accepted families, and persists each candidate as the two
rows the Signals view reads — a ``RawSignalEvent`` (the message) plus an
``ExtractedSignal`` linked to it — then marks the feed ``verified``.

No parser rules: the miner is the extractor, so its structured fields ARE the
signal. Persistence is idempotent — events upsert by (user, channel, message)
and ``record_outcome`` upserts extractions by (user, event) — so re-confirming
the same keys is a no-op, and confirming a superset only adds the new families.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from verasig.domain.event import RawSignalEvent
from verasig.domain.extraction_outcome import ExtractOutcome
from verasig.domain.signal import ExtractedSignal
from verasig.features.feeds import feed_repository, message_repository
from verasig.features.parser_overlay.repository import read_overlay
from verasig.features.rules.mining_signals import candidate_to_event_and_signal
from verasig.features.rules.template_mining import mine_template_groups
from verasig.features.rules.template_mining.types import ChatMessage, TemplateGroup
from verasig.features.signals import event_repository, outcome_repository

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
    groups = _mine_feed(session_factory, user_id, external_id)
    kept = [group for group in groups if group.template_key in accepted]
    pairs = _pairs_of(kept, external_id)
    extracted = _persist(session_factory, user_id, pairs)
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


def _mine_feed(
    session_factory: sessionmaker, user_id: UUID, external_id: int
) -> list[TemplateGroup]:
    with session_factory() as session:
        messages = message_repository.read_messages(session, user_id, external_id)
        overlay = read_overlay(session, user_id)
    chat_messages = [_to_chat_message(message) for message in messages]
    return mine_template_groups(chat_messages, overlay)


def _to_chat_message(message) -> ChatMessage:
    return ChatMessage(
        id=str(message.message_id),
        text=message.text or "",
        date=message.posted_at.isoformat() if message.posted_at else None,
    )


def _pairs_of(
    groups: Sequence[TemplateGroup], external_id: int
) -> list[tuple[RawSignalEvent, ExtractedSignal]]:
    return [
        pair
        for group in groups
        for candidate in group.candidates
        if (pair := candidate_to_event_and_signal(candidate, external_id)) is not None
    ]


def _persist(
    session_factory: sessionmaker,
    user_id: UUID,
    pairs: Sequence[tuple[RawSignalEvent, ExtractedSignal]],
) -> int:
    if not pairs:
        return 0
    with session_factory() as session:
        _persist_events(session, user_id, [event for event, _ in pairs])
        event_id_by_message = _persisted_event_ids(session, user_id, pairs)
        extracted = _persist_signals(session, user_id, pairs, event_id_by_message)
        session.commit()
        return extracted


def _persist_events(
    session: Session, user_id: UUID, events: Sequence[RawSignalEvent]
) -> None:
    event_repository.insert_signal_events(session, user_id, list(events))
    session.flush()


def _persisted_event_ids(
    session: Session,
    user_id: UUID,
    pairs: Sequence[tuple[RawSignalEvent, ExtractedSignal]],
) -> dict[int, UUID]:
    """Resolve each signal to the row that actually persisted for its message.

    ``insert_signal_events`` is on-conflict-do-nothing, so a pre-existing event
    keeps its own id and the freshly-minted one is discarded. Re-reading the
    stored events yields the authoritative (message -> event id) map to link
    against, never an orphaned id.
    """
    channel_id = pairs[0][0].channel_id
    return {
        event.message_id: event.id
        for event in event_repository.read_signal_events(session, user_id, channel_id)
    }


def _persist_signals(
    session: Session,
    user_id: UUID,
    pairs: Sequence[tuple[RawSignalEvent, ExtractedSignal]],
    event_id_by_message: dict[int, UUID],
) -> int:
    extracted = 0
    for event, signal in pairs:
        persisted_event_id = event_id_by_message.get(event.message_id)
        if persisted_event_id is None:
            continue
        linked = signal.model_copy(update={"event_id": persisted_event_id})
        outcome = ExtractOutcome(signal=linked)
        outcome_repository.record_outcome(session, outcome, user_id)
        extracted += 1
    return extracted


def _mark_verified(
    session_factory: sessionmaker, user_id: UUID, external_id: int
) -> str:
    with session_factory() as session:
        feed_repository.set_status(session, user_id, external_id, "verified")
        session.commit()
    return "verified"
