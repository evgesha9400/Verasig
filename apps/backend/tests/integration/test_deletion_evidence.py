"""Durable deletion-evidence persistence (ADR 0008).

`DeletedSignalEvidence` is the third storage class: durable, NOT recomputable
(the live snapshot it is diffed against is ephemeral). One row per
(channel_id, message_id) — re-upsert is +0, a SUSPECTED upgrades to CONFIRMED but
a CONFIRMED never downgrades, and the first-noticed `detected_at` is preserved.
"""

from datetime import datetime, timezone
from uuid import UUID

import pytest
from fakes import FakeSource
from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import Side, Signal
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import (
    deletion_repository,
    feed_repository,
    message_repository,
)
from verasig.features.feeds.deletion_rescan import RescanAborted, rescan
from verasig.features.signals import outcome_repository

_CHANNEL_ID = 7
_USER_ID = UUID("90000000-0000-0000-0000-000000000001")
_FIRST = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
_LATER = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)


def _channel() -> TelegramChannel:
    return TelegramChannel(
        channel_id=_CHANNEL_ID,
        handle="pilot",
        title="Pilot",
        is_private=False,
        first_seen_at=_FIRST,
    )


def _account() -> UserAccount:
    return UserAccount(
        id=_USER_ID,
        email="deletion@example.com",
        password_hash="hash",
        first_name="Ada",
        last_name="Lovelace",
        plan=Plan.FREE,
        pending_email=None,
        cancel_at=None,
        created_at=_FIRST,
    )


def _seed_channel(session_factory) -> None:
    with session_factory() as session:
        account_repository.insert_account(session, _account())
        insert_source(session, _USER_ID)
        feed_repository.create_feed(session, _USER_ID, _channel(), _FIRST)
        session.commit()


def _confirmed(
    message_id: int,
    detected_at: datetime,
    text: str = "gone",
    *,
    was_candidate: bool = True,
) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        channel_id=_CHANNEL_ID,
        message_id=message_id,
        confidence=DeletionConfidence.CONFIRMED,
        method=DeletionMethod.SNAPSHOT_DIFF,
        original_text=text,
        first_seen_at=_FIRST,
        detected_at=detected_at,
        was_signal_candidate=was_candidate,
    )


def _suspected(message_id: int, detected_at: datetime) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        channel_id=_CHANNEL_ID,
        message_id=message_id,
        confidence=DeletionConfidence.SUSPECTED,
        method=DeletionMethod.ID_GAP,
        detected_at=detected_at,
        was_signal_candidate=False,
    )


def _upsert(session_factory, evidence: list[DeletedSignalEvidence]) -> int:
    with session_factory() as session:
        count = deletion_repository.upsert_deletion_evidence(
            session, _USER_ID, evidence
        )
        session.commit()
        return count


def _read(session_factory) -> list[DeletedSignalEvidence]:
    with session_factory() as session:
        return deletion_repository.read_deletion_evidence(
            session, _USER_ID, _CHANNEL_ID
        )


def test_upsert_then_read_round_trips_confirmed_and_suspected(session_factory):
    _seed_channel(session_factory)
    inserted = _upsert(session_factory, [_confirmed(2, _FIRST), _suspected(4, _FIRST)])
    assert inserted == 2
    stored = {item.message_id: item for item in _read(session_factory)}
    assert stored[2].confidence is DeletionConfidence.CONFIRMED
    assert stored[2].method is DeletionMethod.SNAPSHOT_DIFF
    assert stored[2].original_text == "gone"
    assert stored[2].first_seen_at == _FIRST
    assert stored[2].was_signal_candidate is True
    assert stored[4].confidence is DeletionConfidence.SUSPECTED
    assert stored[4].method is DeletionMethod.ID_GAP
    assert stored[4].original_text is None
    assert stored[4].first_seen_at is None


def test_reupsert_same_state_is_zero_and_preserves_detected_at(session_factory):
    _seed_channel(session_factory)
    _upsert(session_factory, [_confirmed(2, _FIRST)])
    again = _upsert(session_factory, [_confirmed(2, _LATER)])  # same state, later clock
    assert again == 0  # guarded WHERE makes a same-state re-run a true no-op
    stored = _read(session_factory)
    assert len(stored) == 1
    assert stored[0].detected_at == _FIRST  # first-noticed preserved


def test_suspected_upgrades_to_confirmed_preserving_detected_at(session_factory):
    _seed_channel(session_factory)
    _upsert(session_factory, [_suspected(5, _FIRST)])
    upgraded = _upsert(session_factory, [_confirmed(5, _LATER, text="was a signal")])
    assert upgraded == 1
    stored = _read(session_factory)
    assert len(stored) == 1
    assert stored[0].confidence is DeletionConfidence.CONFIRMED
    assert stored[0].method is DeletionMethod.SNAPSHOT_DIFF
    assert stored[0].original_text == "was a signal"
    assert stored[0].was_signal_candidate is True
    assert stored[0].detected_at == _FIRST  # first-noticed wins, not _LATER


def test_confirmed_never_downgrades_to_suspected(session_factory):
    _seed_channel(session_factory)
    _upsert(session_factory, [_confirmed(2, _FIRST, text="real signal")])
    downgrade = _upsert(session_factory, [_suspected(2, _LATER)])
    assert downgrade == 0
    stored = _read(session_factory)
    assert len(stored) == 1
    assert stored[0].confidence is DeletionConfidence.CONFIRMED
    assert stored[0].original_text == "real signal"  # content retained


# --- Gated rescan orchestration (re-fetch live ids -> detect -> persist) -------


def _message(message_id: int, text: str) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=_CHANNEL_ID,
        message_id=message_id,
        text=text,
        posted_at=_FIRST,
        captured_at=_FIRST,
        has_media=False,
        raw_payload={},
    )


def _seed_corpus(session_factory) -> None:
    """Channel + messages {1,2,3}; message 2 is a signal candidate (has a Signal)."""
    with session_factory() as session:
        account_repository.insert_account(session, _account())
        insert_source(session, _USER_ID)
        feed_repository.create_feed(session, _USER_ID, _channel(), _FIRST)
        message_repository.insert_messages(
            session,
            _USER_ID,
            [
                _message(1, "gm frens"),
                _message(2, "BTC long 65k"),
                _message(3, "still chatting"),
            ],
        )
        outcome_repository.insert_signals(
            session,
            [
                Signal(
                    channel_id=_CHANNEL_ID,
                    message_id=2,
                    candidate_text="BTC long 65k",
                    symbol="BTCUSDT",
                    side=Side.LONG,
                )
            ],
            _USER_ID,
        )
        session.commit()


def _summary(session_factory):
    with session_factory() as session:
        return deletion_repository.summarize_deletions(
            session, _USER_ID, [_CHANNEL_ID]
        )[_CHANNEL_ID]


def test_summarize_deletions_counts_confirmed_only(session_factory):
    _seed_channel(session_factory)
    _upsert(session_factory, [_confirmed(2, _LATER), _suspected(4, _LATER)])

    summary = _summary(session_factory)

    # suspected id-gaps are internal-only (hygiene); the user-facing summary counts
    # confirmed deletions only. The confirmed row is a signal candidate.
    assert summary.deleted_count == 1
    assert summary.signal_deletion is True


def test_summarize_deletions_counts_signal_deletions_by_candidacy(session_factory):
    _seed_channel(session_factory)
    _upsert(
        session_factory,
        [
            _confirmed(2, _LATER, "BTC long 65k", was_candidate=True),
            _confirmed(3, _LATER, "gm", was_candidate=False),
        ],
    )

    summary = _summary(session_factory)

    # `was_signal_candidate` is authoritative: a confirmed deletion of a candidate
    # is a signal deletion; confirmed chatter is counted but is not.
    assert summary.deleted_count == 2
    assert summary.deleted_signal_count == 1
    assert summary.signal_deletion is True


def _source(live_ids: set[int]) -> FakeSource:
    return FakeSource(_channel(), [], live_ids=live_ids)


async def test_rescan_persists_confirmed_signal_chatter_and_suspected_gap(
    session_factory,
):
    _seed_corpus(session_factory)
    # live = {1, 5}: 2 + 3 are gone (confirmed), id 4 is a never-captured gap
    result = await rescan(_source({1, 5}), _USER_ID, "@pilot", session_factory)
    assert (result.external_id, result.confirmed, result.suspected) == (
        _CHANNEL_ID,
        2,
        1,
    )
    assert result.written == 3
    stored = {item.message_id: item for item in _read(session_factory)}
    assert stored[2].confidence is DeletionConfidence.CONFIRMED
    assert stored[2].original_text == "BTC long 65k"
    assert stored[2].was_signal_candidate is True  # signal deletion
    assert stored[3].confidence is DeletionConfidence.CONFIRMED
    assert stored[3].was_signal_candidate is False  # chatter stored for audit
    assert stored[4].confidence is DeletionConfidence.SUSPECTED
    assert stored[4].original_text is None


async def test_rescan_rerun_writes_zero(session_factory):
    _seed_corpus(session_factory)
    await rescan(_source({1, 5}), _USER_ID, "@pilot", session_factory)
    rerun = await rescan(_source({1, 5}), _USER_ID, "@pilot", session_factory)
    assert rerun.written == 0  # same state => true no-op
    assert len(_read(session_factory)) == 3  # no new rows


async def test_rescan_empty_live_snapshot_aborts_without_writing(session_factory):
    _seed_corpus(session_factory)
    with pytest.raises(RescanAborted):
        await rescan(_source(set()), _USER_ID, "@pilot", session_factory)
    assert _read(session_factory) == []  # inaccessible channel is not a mass deletion


def test_upsert_chunks_evidence_past_the_bind_parameter_limit(session_factory):
    _seed_channel(session_factory)
    # 7,000 rows x 10 columns = 70,000 binds: one INSERT would exceed PostgreSQL's
    # 65,535 limit, so this only succeeds when the upsert is chunked.
    evidence = [_suspected(message_id, _LATER) for message_id in range(1, 7001)]

    assert _upsert(session_factory, evidence) == 7000
    assert len(_read(session_factory)) == 7000


class _CapturesDuringWalk(FakeSource):
    """Captures a brand-new message while the live walk is in flight."""

    def __init__(self, session_factory, live_ids: set[int]) -> None:
        super().__init__(_channel(), [], live_ids=live_ids)
        self._session_factory = session_factory

    async def live_message_ids(self, channel_id, on_progress=None) -> set[int]:
        live = await super().live_message_ids(channel_id, on_progress)
        with self._session_factory() as session:
            message_repository.insert_messages(
                session, _USER_ID, [_message(6, "posted mid-walk")]
            )
            session.commit()
        return live


async def test_rescan_never_confirms_a_message_captured_during_the_live_walk(
    session_factory,
):
    _seed_corpus(session_factory)

    result = await rescan(
        _CapturesDuringWalk(session_factory, {1, 2, 3, 5}),
        _USER_ID,
        "@pilot",
        session_factory,
    )

    stored = {item.message_id: item for item in _read(session_factory)}
    assert 6 not in stored  # absent from the walk only because it was too new
    assert result.confirmed == 0
