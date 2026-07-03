from uuid import UUID

from sqlalchemy.orm import Session

from verasig.features.rules import repository as rule_repository
from verasig.features.signals import event_repository, outcome_repository
from verasig.features.signals.extract_service import ExtractService


def rematerialize_signal_outcomes(
    session: Session, user_id: UUID, channel_id: int
) -> tuple[int, int]:
    """Re-extract EVERY event with the feed's current parser rules (ADR 0015).

    Used after Mining Confirm changes the ruleset: `record_outcome` upserts by
    (user_id, event_id) and flips winner/loser + drift, so a full re-run is
    idempotent. Returns (extracted, unrecognized) counts.
    """
    events = event_repository.read_signal_events(session, user_id, channel_id)
    parser_rules = rule_repository.read_parser_rules(session, channel_id, user_id)
    service = ExtractService(parser_rules)
    extracted = unrecognized = 0
    for event in events:
        outcome = service.extract(event)
        outcome_repository.record_outcome(session, outcome, user_id)
        if outcome.signal is not None:
            extracted += 1
        else:
            unrecognized += 1
    return extracted, unrecognized


def materialize_missing_signal_outcomes(
    session: Session, user_id: UUID, channel_id: int
) -> None:
    events = event_repository.read_signal_events(session, user_id, channel_id)
    extracted_event_ids = {
        outcome.event_id
        for outcome in outcome_repository.read_extracted_signals(
            session, channel_id, user_id
        )
    }
    unrecognized_event_ids = {
        outcome.event_id
        for outcome in outcome_repository.read_unrecognized_signals(
            session, channel_id, user_id
        )
    }
    parser_rules = rule_repository.read_parser_rules(session, channel_id, user_id)
    retry_unrecognized = bool(parser_rules)
    service = ExtractService(parser_rules)
    for event in events:
        if event.id in extracted_event_ids:
            continue
        if event.id in unrecognized_event_ids and not retry_unrecognized:
            continue
        outcome_repository.record_outcome(session, service.extract(event), user_id)
