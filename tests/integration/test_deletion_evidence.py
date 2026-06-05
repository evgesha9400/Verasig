"""Durable deletion-evidence persistence (ADR 0008).

`DeletedSignalEvidence` is the third storage class: durable, NOT recomputable
(the live snapshot it is diffed against is ephemeral). One row per
(channel_id, message_id) — re-upsert is +0, a SUSPECTED upgrades to CONFIRMED but
a CONFIRMED never downgrades, and the first-noticed `detected_at` is preserved.
"""

from datetime import datetime, timezone

from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.storage import repositories as repo

_CHANNEL_ID = 7
_FIRST = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
_LATER = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)


def _seed_channel(session_factory) -> None:
    with session_factory() as session:
        repo.upsert_channel(
            session,
            TelegramChannel(
                channel_id=_CHANNEL_ID,
                handle="pilot",
                title="Pilot",
                is_private=False,
                first_seen_at=_FIRST,
            ),
        )
        session.commit()


def _confirmed(
    message_id: int, detected_at: datetime, text: str = "gone"
) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        channel_id=_CHANNEL_ID,
        message_id=message_id,
        confidence=DeletionConfidence.CONFIRMED,
        method=DeletionMethod.SNAPSHOT_DIFF,
        original_text=text,
        first_seen_at=_FIRST,
        detected_at=detected_at,
        was_signal_candidate=True,
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
        count = repo.upsert_deletion_evidence(session, evidence)
        session.commit()
        return count


def _read(session_factory) -> list[DeletedSignalEvidence]:
    with session_factory() as session:
        return repo.read_deletion_evidence(session, _CHANNEL_ID)


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
