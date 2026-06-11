"""ProviderScore evidence refs resolve back to durable stored rows (ADR 0009)."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import (
    EntryType,
    ExtractedSignal,
    ExtractionMethod,
    Side,
    UnrecognizedSignal,
)
from verasig.services.scoring.scorecard import build_provider_score
from verasig.storage import repositories as repo

_CHANNEL_ID = 7
_BASE = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _uuid(suffix: int) -> UUID:
    return UUID(f"20000000-0000-0000-0000-{suffix:012d}")


def _at(days: int) -> datetime:
    return _BASE + timedelta(days=days)


def _channel() -> TelegramChannel:
    return TelegramChannel(
        channel_id=_CHANNEL_ID,
        handle="pilot",
        title="Pilot",
        is_private=False,
        subscriber_count=5000,
        first_seen_at=_BASE,
    )


def _message(message_id: int, days: int, views: int, forwards: int):
    return RawTelegramMessage(
        channel_id=_CHANNEL_ID,
        message_id=message_id,
        text=f"message {message_id}",
        posted_at=_at(days),
        captured_at=_at(days),
        has_media=False,
        views=views,
        forwards=forwards,
        raw_payload={"id": message_id},
    )


def _event(suffix: int, message_id: int) -> RawSignalEvent:
    return RawSignalEvent(
        id=_uuid(suffix),
        channel_id=_CHANNEL_ID,
        message_id=message_id,
        candidate_text="BTC long",
        materialized_by=MaterializationPath.SEED_HEURISTIC,
        created_at=_BASE,
    )


def _signal(signal_id: int, event_id: UUID) -> ExtractedSignal:
    return ExtractedSignal(
        id=_uuid(signal_id),
        event_id=event_id,
        channel_id=_CHANNEL_ID,
        symbol="BTC",
        side=Side.LONG,
        entry_type=EntryType.MARKET,
        stop_loss="64000",
        take_profits=["67000"],
        extraction_method=ExtractionMethod.DETERMINISTIC,
        extracted_at=_BASE,
    )


def _unrecognized(suffix: int, event_id: UUID) -> UnrecognizedSignal:
    return UnrecognizedSignal(
        id=_uuid(suffix),
        event_id=event_id,
        reason="no_match",
        attempted_methods=[ExtractionMethod.DETERMINISTIC],
        created_at=_BASE,
    )


def _id_gap(suffix: int, message_id: int) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        id=_uuid(suffix),
        channel_id=_CHANNEL_ID,
        message_id=message_id,
        confidence=DeletionConfidence.SUSPECTED,
        method=DeletionMethod.ID_GAP,
        detected_at=_BASE,
        was_signal_candidate=False,
    )


def _seed_score_inputs(session_factory) -> None:
    event_a = _event(1, 1)
    event_b = _event(2, 2)
    with session_factory() as session:
        repo.upsert_channel(session, _channel())
        repo.insert_messages(
            session,
            [
                _message(1, 0, views=1000, forwards=100),
                _message(2, 1, views=2000, forwards=200),
                _message(3, 2, views=3000, forwards=300),
            ],
        )
        repo.insert_signal_events(session, [event_a, event_b])
        repo.insert_extracted_signals(session, [_signal(3, event_a.id)])
        repo.insert_unrecognized_signals(session, [_unrecognized(4, event_b.id)])
        repo.upsert_deletion_evidence(session, [_id_gap(5, 4)])
        session.commit()


def _score_from_repo(session_factory):
    with session_factory() as session:
        channel = repo.find_channel(session, "@pilot")
        messages = repo.read_messages(session, _CHANNEL_ID)
        events = repo.read_signal_events(session, _CHANNEL_ID)
        signals = repo.read_extracted_signals(session, _CHANNEL_ID)
        unrecognized = repo.read_unrecognized_signals(session, _CHANNEL_ID)
        deletions = repo.read_deletion_evidence(session, _CHANNEL_ID)
        message_count = repo.count_messages(session, _CHANNEL_ID)
    return build_provider_score(
        channel=channel,
        messages=messages,
        message_count=message_count,
        events=events,
        signals=signals,
        unrecognized=unrecognized,
        deletions=deletions,
        computed_at=_BASE,
    )[0]


def _stored_refs(session_factory) -> set[str]:
    with session_factory() as session:
        messages = repo.read_messages(session, _CHANNEL_ID)
        events = repo.read_signal_events(session, _CHANNEL_ID)
        signals = repo.read_extracted_signals(session, _CHANNEL_ID)
        unrecognized = repo.read_unrecognized_signals(session, _CHANNEL_ID)
        deletions = repo.read_deletion_evidence(session, _CHANNEL_ID)
        message_count = repo.count_messages(session, _CHANNEL_ID)
    refs = {f"channel:{_CHANNEL_ID}"} if message_count == 3 else set()
    refs.update(f"message:{item.channel_id}/{item.message_id}" for item in messages)
    refs.update(f"event:{item.id}" for item in events)
    refs.update(f"signal:{item.id}" for item in signals)
    refs.update(f"unrecognized:{item.id}" for item in unrecognized)
    refs.update(f"deletion:{item.id}" for item in deletions)
    return refs


def test_score_evidence_refs_resolve_to_stored_rows(session_factory):
    _seed_score_inputs(session_factory)

    score = _score_from_repo(session_factory)
    stored_refs = _stored_refs(session_factory)

    assert score.components
    for component in score.components:
        assert component.evidence_refs
        assert set(component.evidence_refs) <= stored_refs
