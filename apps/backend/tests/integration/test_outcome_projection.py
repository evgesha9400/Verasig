"""record_outcome = recomputable per-event projection (ADR 0006, amends 0001).

The winning outcome is upserted ON CONFLICT(event_id); the losing sibling is
deleted; the parser_drift_warning is upserted (fallback hit) or cleared. Re-extract
is +0 and transitions (unrecognized <-> extracted) leave no stale sibling. Raw
tables stay append-only; only this projection is recomputed.
"""

from datetime import datetime, timezone
from decimal import Decimal

from fakes import FakeExtractor

from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.message import RawTelegramMessage
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import Side, TradeIntent
from verasig.features.rules import drift_repository
from verasig.features.signals import event_repository, outcome_repository
from verasig.features.signals.extract_service import ExtractService
from verasig.features.sources import (
    channel_repository,
    message_repository,
)

_LONG_RULE = ParserRule(
    rule_id="r1",
    patterns=[
        r"(?P<symbol>[A-Za-z]{2,10})\s+(?P<side>long|short)"
        r"(?:.*?entry[:\s]+(?P<entry>[\d.,]+k?))?"
    ],
    field_map={"symbol": "symbol", "side": "side", "entry": "entry"},
    side_aliases={"long": "LONG", "short": "SHORT"},
)


def _instant() -> datetime:
    return datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)


def _seed_event(session_factory, text: str) -> RawSignalEvent:
    event = RawSignalEvent(
        channel_id=7,
        message_id=1,
        candidate_text=text,
        materialized_by=MaterializationPath.SEED_HEURISTIC,
    )
    with session_factory() as session:
        channel_repository.upsert_channel(
            session,
            TelegramChannel(
                channel_id=7,
                handle="pilot",
                title="Pilot",
                is_private=False,
                first_seen_at=_instant(),
            ),
        )
        message_repository.insert_messages(
            session,
            [
                RawTelegramMessage(
                    channel_id=7,
                    message_id=1,
                    text=text,
                    posted_at=_instant(),
                    captured_at=_instant(),
                    has_media=False,
                    raw_payload={},
                )
            ],
        )
        event_repository.insert_signal_events(session, [event])
        session.commit()
    return event


def _record(session_factory, outcome) -> None:
    with session_factory() as session:
        outcome_repository.record_outcome(session, outcome)
        session.commit()


def test_record_outcome_persists_extracted_and_reextract_is_idempotent(session_factory):
    event = _seed_event(session_factory, "BTC long entry 65000")
    _record(session_factory, ExtractService(rules=[_LONG_RULE]).extract(event))
    _record(session_factory, ExtractService(rules=[_LONG_RULE]).extract(event))
    with session_factory() as session:
        stored = outcome_repository.read_extracted_signals(session, 7)
    assert len(stored) == 1  # upsert on event_id, never duplicated
    assert stored[0].symbol == "BTCUSDT"


def test_record_outcome_persists_parser_drift_one_to_one(session_factory):
    event = _seed_event(session_factory, "no rule will match this")
    intent = TradeIntent(symbol="BTC", side=Side.LONG, stop_loss=Decimal("64000"))
    outcome = ExtractService(rules=[], fallback=FakeExtractor(returns=intent)).extract(
        event
    )
    _record(session_factory, outcome)
    with session_factory() as session:
        signals = outcome_repository.read_extracted_signals(session, 7)
        drifts = drift_repository.read_parser_drift_warnings(session, 7)
    assert len(signals) == 1 and len(drifts) == 1  # exactly one drift per fallback hit
    assert drifts[0].event_id == event.id
    assert drifts[0].fallback_signal_id == signals[0].id  # stamped with the stored id


def test_record_outcome_reextract_keeps_pk_and_drift_stays_consistent(session_factory):
    event = _seed_event(session_factory, "no rule will match this")
    intent = TradeIntent(symbol="BTC", side=Side.LONG)
    service = ExtractService(rules=[], fallback=FakeExtractor(returns=intent))
    _record(session_factory, service.extract(event))
    with session_factory() as session:
        first_id = outcome_repository.read_extracted_signals(session, 7)[0].id
    _record(session_factory, service.extract(event))  # fresh signal id, same event
    with session_factory() as session:
        signals = outcome_repository.read_extracted_signals(session, 7)
        drifts = drift_repository.read_parser_drift_warnings(session, 7)
    assert len(signals) == 1 and signals[0].id == first_id  # original PK preserved
    assert drifts[0].fallback_signal_id == first_id  # drift re-stamped to stored id


def test_record_outcome_transition_unrecognized_to_extracted_drops_sibling(
    session_factory,
):
    event = _seed_event(session_factory, "BTC long entry 65000")
    _record(session_factory, ExtractService(rules=[]).extract(event))  # no_match
    with session_factory() as session:
        assert len(outcome_repository.read_unrecognized_signals(session, 7)) == 1
        assert outcome_repository.read_extracted_signals(session, 7) == []
    _record(session_factory, ExtractService(rules=[_LONG_RULE]).extract(event))
    with session_factory() as session:
        assert len(outcome_repository.read_extracted_signals(session, 7)) == 1
        assert (
            outcome_repository.read_unrecognized_signals(session, 7) == []
        )  # stale sibling gone


def test_record_outcome_transition_extracted_to_unrecognized_clears_drift(
    session_factory,
):
    event = _seed_event(session_factory, "no rule will match this")
    intent = TradeIntent(symbol="BTC", side=Side.LONG)
    _record(
        session_factory,
        ExtractService(rules=[], fallback=FakeExtractor(returns=intent)).extract(event),
    )
    with session_factory() as session:
        assert len(outcome_repository.read_extracted_signals(session, 7)) == 1
        assert len(drift_repository.read_parser_drift_warnings(session, 7)) == 1
    _record(session_factory, ExtractService(rules=[]).extract(event))  # now a miss
    with session_factory() as session:
        assert len(outcome_repository.read_unrecognized_signals(session, 7)) == 1
        assert (
            outcome_repository.read_extracted_signals(session, 7) == []
        )  # sibling gone
        assert (
            drift_repository.read_parser_drift_warnings(session, 7) == []
        )  # drift cleared
