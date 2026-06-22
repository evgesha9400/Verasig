from uuid import UUID

from sqlalchemy.orm import Session

from verasig.features.rules import repository as rule_repository
from verasig.features.signals import event_repository, outcome_repository
from verasig.features.signals.extract_service import ExtractService


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
