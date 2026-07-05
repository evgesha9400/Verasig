from uuid import UUID

from sqlalchemy.orm import Session

from verasig.domain.extraction_outcome import ExtractOutcome
from verasig.domain.signal import UnrecognizedSignal
from verasig.features.signals import event_repository, outcome_repository


def materialize_missing_signal_outcomes(
    session: Session, user_id: UUID, channel_id: int
) -> None:
    """Give every stored event exactly one outcome (data-contracts.md §3).

    The miner writes an `ExtractedSignal` for each candidate it confirms; a
    stored event it did not recognize has no outcome yet. This projects those
    gaps as `UnrecognizedSignal`s so scoring, hygiene, and the lifecycle fold
    always see the complete one-of set. Idempotent: settled events are skipped.
    """
    events = event_repository.read_signal_events(session, user_id, channel_id)
    settled_event_ids = _settled_event_ids(session, user_id, channel_id)
    for event in events:
        if event.id in settled_event_ids:
            continue
        outcome = ExtractOutcome(
            unrecognized=UnrecognizedSignal(event_id=event.id, reason="no_match")
        )
        outcome_repository.record_outcome(session, outcome, user_id)


def _settled_event_ids(session: Session, user_id: UUID, channel_id: int) -> set[UUID]:
    extracted = {
        outcome.event_id
        for outcome in outcome_repository.read_extracted_signals(
            session, channel_id, user_id
        )
    }
    unrecognized = {
        outcome.event_id
        for outcome in outcome_repository.read_unrecognized_signals(
            session, channel_id, user_id
        )
    }
    return extracted | unrecognized
