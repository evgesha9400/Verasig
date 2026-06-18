"""Advisory candidate derivation + parser sweep over stored messages (ADR 0005).

`derive_candidates` materializes `RawSignalEvent`s from a feed's captured
messages: a distilled `FilterRule` wins (provenance `FILTER_RULE`), else the
recall-first seed heuristic (`SEED_HEURISTIC`). `sweep_advisory` runs the cheap
deterministic parser over **all** messages; a parse hit on a message that is *not*
already a candidate is a filter miss — it late-materializes a `PARSER_BACKFILL`
event and emits exactly one `FilterDriftWarning`. Both page by message-id cursor
and commit per batch (spec §4.1: bounded, never the full history in RAM). Capture
is user-owned, so every step is scoped by `user_id`.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from verasig.domain.drift import FilterDriftWarning, MissDiscoveredBy
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.filter_rule import FilterRule
from verasig.domain.market_ports import Exchange
from verasig.domain.message import RawTelegramMessage
from verasig.domain.parser_rule import ParserRule
from verasig.features.feeds import message_repository
from verasig.features.feeds.candidate_filter import apply_filter_rule, seed_candidate
from verasig.features.rules import drift_repository
from verasig.features.signals import event_repository
from verasig.features.signals.deterministic_parser import parse


def _filter_event(
    message: RawTelegramMessage, filter_rules: Sequence[FilterRule]
) -> RawSignalEvent | None:
    if not message.text:
        return None
    for rule in filter_rules:
        if apply_filter_rule(rule, message.text):
            return RawSignalEvent(
                channel_id=message.channel_id,
                message_id=message.message_id,
                candidate_text=message.text,
                materialized_by=MaterializationPath.FILTER_RULE,
                filter_rule_id=rule.rule_id,
            )
    return None


def _derive_event(
    message: RawTelegramMessage, exchange: Exchange, filter_rules: Sequence[FilterRule]
) -> RawSignalEvent | None:
    # distilled FilterRule wins over the cold-start seed (ADR 0005)
    return _filter_event(message, filter_rules) or seed_candidate(message, exchange)


def _pages(
    session_factory: sessionmaker, user_id: UUID, external_id: int, batch_size: int
):
    cursor = 0
    while True:
        with session_factory() as session:
            page = message_repository.read_message_page(
                session, user_id, external_id, cursor, batch_size
            )
        if not page:
            return
        yield page
        cursor = page[-1].message_id


def derive_candidates(
    session_factory: sessionmaker,
    user_id: UUID,
    external_id: int,
    exchange: Exchange,
    *,
    filter_rules: Sequence[FilterRule] = (),
    batch_size: int = 200,
) -> int:
    created = 0
    for page in _pages(session_factory, user_id, external_id, batch_size):
        events = [
            event
            for message in page
            if (event := _derive_event(message, exchange, filter_rules)) is not None
        ]
        with session_factory() as session:
            created += event_repository.insert_signal_events(session, user_id, events)
            session.commit()
    return created


def _parses(parser_rules: list[ParserRule], event: RawSignalEvent) -> bool:
    return any(parse(rule, event.candidate_text) is not None for rule in parser_rules)


def sweep_advisory(
    session_factory: sessionmaker,
    user_id: UUID,
    external_id: int,
    parser_rules: list[ParserRule],
    user_id: UUID,
    *,
    batch_size: int = 200,
) -> tuple[int, int]:
    with session_factory() as session:
        already_candidate = message_repository.candidate_message_ids(
            session, user_id, external_id
        )
    new_events = new_warnings = 0
    for page in _pages(session_factory, user_id, external_id, batch_size):
        events, warnings = _recover_misses(
            page, external_id, already_candidate, parser_rules
        )
        with session_factory() as session:
            new_events += event_repository.insert_signal_events(
                session, user_id, events
            )
            new_warnings += drift_repository.insert_drift_warnings(
                session, warnings, user_id
            )
            session.commit()
    return new_events, new_warnings


def _recover_misses(
    page: list[RawTelegramMessage],
    external_id: int,
    already_candidate: set[int],
    parser_rules: list[ParserRule],
) -> tuple[list[RawSignalEvent], list[FilterDriftWarning]]:
    events: list[RawSignalEvent] = []
    warnings: list[FilterDriftWarning] = []
    for message in page:
        if message.message_id in already_candidate or not message.text:
            continue
        event = RawSignalEvent(
            channel_id=external_id,
            message_id=message.message_id,
            candidate_text=message.text,
            materialized_by=MaterializationPath.PARSER_BACKFILL,
        )
        if not _parses(parser_rules, event):
            continue
        events.append(event)
        warnings.append(
            FilterDriftWarning(
                channel_id=external_id,
                message_id=message.message_id,
                miss_discovered_by=MissDiscoveredBy.PARSER_BACKFILL,
                event_id=event.id,
            )
        )
    return events, warnings
