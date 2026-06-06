from datetime import datetime, timezone
from uuid import UUID

from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.services.scoring.hygiene import (
    ExcludedMeasurement,
    HygieneMeasurement,
    measure_deletion_behaviour,
)

_BASE = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _uuid(suffix: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{suffix:012d}")


def _event(suffix: int, message_id: int) -> RawSignalEvent:
    return RawSignalEvent(
        id=_uuid(suffix),
        channel_id=7,
        message_id=message_id,
        candidate_text="BTC long",
        materialized_by=MaterializationPath.SEED_HEURISTIC,
        created_at=_BASE,
    )


def _deletion(suffix: int, message_id: int) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        id=_uuid(suffix),
        channel_id=7,
        message_id=message_id,
        confidence=DeletionConfidence.CONFIRMED,
        method=DeletionMethod.SNAPSHOT_DIFF,
        detected_at=_BASE,
        was_signal_candidate=True,
    )


def test_deletion_behaviour_scores_zero_deletions_as_one_with_event_refs():
    measurement = measure_deletion_behaviour(events=[_event(1, 10)], deletions=[])

    assert isinstance(measurement, HygieneMeasurement)
    assert measurement.name == "deletion_behaviour"
    assert measurement.raw_value == 1.0
    assert measurement.normalized == 1.0
    assert measurement.evidence_refs == ["event:00000000-0000-0000-0000-000000000001"]


def test_deletion_behaviour_excludes_empty_candidate_denominator():
    measurement = measure_deletion_behaviour(events=[], deletions=[_deletion(2, 10)])

    assert isinstance(measurement, ExcludedMeasurement)
    assert measurement.name == "deletion_behaviour"
    assert measurement.note == "deletion_behaviour: not measured — no signal candidates"
