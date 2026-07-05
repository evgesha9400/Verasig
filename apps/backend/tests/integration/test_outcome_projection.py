"""record_outcome = recomputable per-event projection (ADR 0006, amends 0001).

The winning outcome is upserted ON CONFLICT(event_id) and the losing sibling is
deleted, so a transition (unrecognized <-> extracted) leaves no stale sibling and
re-recording the same winner is +0. Raw tables stay append-only; only this
projection is recomputed.
"""

from datetime import datetime, timezone
from uuid import UUID

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.extraction_outcome import ExtractOutcome
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import ExtractedSignal, Side, UnrecognizedSignal
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import (
    feed_repository,
    message_repository,
)
from verasig.features.signals import event_repository, outcome_repository
from verasig.features.signals.materialization import materialize_missing_signal_outcomes

_USER_ID = UUID("40000000-0000-0000-0000-000000000001")


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
        account_repository.insert_account(
            session,
            UserAccount(
                id=_USER_ID,
                email="projection@example.com",
                password_hash="hash",
                first_name="Ada",
                last_name="Lovelace",
                plan=Plan.OBSERVER,
                pending_email=None,
                cancel_at=None,
                created_at=_instant(),
            ),
        )
        insert_source(session, _USER_ID)
        feed_repository.create_feed(
            session,
            _USER_ID,
            TelegramChannel(
                channel_id=7,
                handle="pilot",
                title="Pilot",
                is_private=False,
                first_seen_at=_instant(),
            ),
            _instant(),
        )
        message_repository.insert_messages(
            session,
            _USER_ID,
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
        event_repository.insert_signal_events(session, _USER_ID, [event])
        session.commit()
    return event


def _extracted(event: RawSignalEvent) -> ExtractOutcome:
    return ExtractOutcome(
        signal=ExtractedSignal(
            event_id=event.id,
            channel_id=event.channel_id,
            symbol="BTCUSDT",
            side=Side.LONG,
        )
    )


def _unrecognized(event: RawSignalEvent) -> ExtractOutcome:
    return ExtractOutcome(
        unrecognized=UnrecognizedSignal(event_id=event.id, reason="no_match")
    )


def _record(session_factory, outcome: ExtractOutcome) -> None:
    with session_factory() as session:
        outcome_repository.record_outcome(session, outcome, _USER_ID)
        session.commit()


def test_record_outcome_persists_extracted_and_rerecord_is_idempotent(session_factory):
    event = _seed_event(session_factory, "BTC long entry 65000")
    _record(session_factory, _extracted(event))
    _record(session_factory, _extracted(event))
    with session_factory() as session:
        stored = outcome_repository.read_extracted_signals(session, 7, _USER_ID)
    assert len(stored) == 1  # upsert on event_id, never duplicated
    assert stored[0].symbol == "BTCUSDT"


def test_record_outcome_transition_unrecognized_to_extracted_drops_sibling(
    session_factory,
):
    event = _seed_event(session_factory, "BTC long entry 65000")
    _record(session_factory, _unrecognized(event))
    with session_factory() as session:
        assert (
            len(outcome_repository.read_unrecognized_signals(session, 7, _USER_ID)) == 1
        )
        assert outcome_repository.read_extracted_signals(session, 7, _USER_ID) == []
    _record(session_factory, _extracted(event))
    with session_factory() as session:
        assert len(outcome_repository.read_extracted_signals(session, 7, _USER_ID)) == 1
        assert (
            outcome_repository.read_unrecognized_signals(session, 7, _USER_ID) == []
        )  # stale sibling gone


def test_record_outcome_transition_extracted_to_unrecognized_drops_sibling(
    session_factory,
):
    event = _seed_event(session_factory, "BTC long entry 65000")
    _record(session_factory, _extracted(event))
    with session_factory() as session:
        assert len(outcome_repository.read_extracted_signals(session, 7, _USER_ID)) == 1
    _record(session_factory, _unrecognized(event))
    with session_factory() as session:
        assert (
            len(outcome_repository.read_unrecognized_signals(session, 7, _USER_ID)) == 1
        )
        assert (
            outcome_repository.read_extracted_signals(session, 7, _USER_ID) == []
        )  # sibling gone


def test_materialize_projects_uncovered_event_as_unrecognized(session_factory):
    # The miner writes signals on Confirm; an event it never recognized has no
    # outcome. materialize fills the gap so the one-of invariant always holds.
    event = _seed_event(session_factory, "gm — just chatter, no trade")
    with session_factory() as session:
        materialize_missing_signal_outcomes(session, _USER_ID, 7)
        session.commit()
    with session_factory() as session:
        unrecognized = outcome_repository.read_unrecognized_signals(
            session, 7, _USER_ID
        )
        assert [item.event_id for item in unrecognized] == [event.id]
        assert unrecognized[0].reason == "no_match"
        assert outcome_repository.read_extracted_signals(session, 7, _USER_ID) == []


def test_materialize_skips_events_the_miner_already_settled(session_factory):
    event = _seed_event(session_factory, "BTC long entry 65000")
    _record(session_factory, _extracted(event))  # miner confirmed it on Confirm
    with session_factory() as session:
        materialize_missing_signal_outcomes(session, _USER_ID, 7)
        session.commit()
    with session_factory() as session:
        assert len(outcome_repository.read_extracted_signals(session, 7, _USER_ID)) == 1
        assert outcome_repository.read_unrecognized_signals(session, 7, _USER_ID) == []
