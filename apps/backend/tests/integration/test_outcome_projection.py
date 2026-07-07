"""record_outcome = recomputable per-event projection (ADR 0006, amends 0001).

The extraction is upserted ON CONFLICT(user_id, event_id), so re-recording the
same extraction is a no-op change and never duplicates. A "miss" is not stored:
it is a raw_signal_event with no extracted_signal, recovered by anti-join via
``read_unrecognized_event_ids``.
"""

from datetime import datetime, timezone
from uuid import UUID

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import ExtractedSignal, Side
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import (
    feed_repository,
    message_repository,
)
from verasig.features.signals import event_repository, outcome_repository

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


def _extracted(event: RawSignalEvent) -> ExtractedSignal:
    return ExtractedSignal(
        event_id=event.id,
        channel_id=event.channel_id,
        symbol="BTCUSDT",
        side=Side.LONG,
    )


def _record(session_factory, signal: ExtractedSignal) -> None:
    with session_factory() as session:
        outcome_repository.record_outcome(session, signal, _USER_ID)
        session.commit()


def test_record_outcome_persists_extracted_and_rerecord_is_idempotent(session_factory):
    event = _seed_event(session_factory, "BTC long entry 65000")
    _record(session_factory, _extracted(event))
    _record(session_factory, _extracted(event))
    with session_factory() as session:
        stored = outcome_repository.read_extracted_signals(session, 7, _USER_ID)
    assert len(stored) == 1  # upsert on (user_id, event_id), never duplicated
    assert stored[0].symbol == "BTCUSDT"


def test_uncovered_event_is_a_miss_by_anti_join(session_factory):
    # An event the miner never recognized has no extracted_signal; it surfaces as
    # a miss through the anti-join, with nothing stored for it.
    event = _seed_event(session_factory, "gm — just chatter, no trade")
    with session_factory() as session:
        assert outcome_repository.read_extracted_signals(session, 7, _USER_ID) == []
        assert outcome_repository.read_unrecognized_event_ids(session, 7, _USER_ID) == [
            event.id
        ]


def test_recording_extraction_removes_event_from_the_miss_set(session_factory):
    event = _seed_event(session_factory, "BTC long entry 65000")
    with session_factory() as session:
        assert outcome_repository.read_unrecognized_event_ids(session, 7, _USER_ID) == [
            event.id
        ]
    _record(session_factory, _extracted(event))
    with session_factory() as session:
        assert len(outcome_repository.read_extracted_signals(session, 7, _USER_ID)) == 1
        assert (
            outcome_repository.read_unrecognized_event_ids(session, 7, _USER_ID) == []
        )
