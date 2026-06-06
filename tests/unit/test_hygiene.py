from datetime import datetime, timezone
from uuid import UUID

import pytest

from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.signal import (
    EntryType,
    ExtractedSignal,
    ExtractionMethod,
    Side,
    UnrecognizedSignal,
)
from verasig.services.scoring.hygiene import (
    ExcludedMeasurement,
    HygieneMeasurement,
    measure_completeness,
    measure_deletion_behaviour,
    measure_evidence_availability,
    measure_parser_confidence,
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


def _id_gap(suffix: int, message_id: int) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        id=_uuid(suffix),
        channel_id=7,
        message_id=message_id,
        confidence=DeletionConfidence.SUSPECTED,
        method=DeletionMethod.ID_GAP,
        detected_at=_BASE,
        was_signal_candidate=False,
    )


def _signal(
    suffix: int,
    *,
    entry_type: EntryType | None = None,
    entry_low: str | None = None,
    stop_loss: str | None = None,
    take_profits: list[str] | None = None,
) -> ExtractedSignal:
    return ExtractedSignal(
        id=_uuid(suffix),
        event_id=_uuid(suffix + 100),
        channel_id=7,
        symbol="BTC",
        side=Side.LONG,
        entry_type=entry_type,
        entry_low=entry_low,
        stop_loss=stop_loss,
        take_profits=[] if take_profits is None else take_profits,
        extracted_at=_BASE,
    )


def _unrecognized(suffix: int) -> UnrecognizedSignal:
    return UnrecognizedSignal(
        id=_uuid(suffix),
        event_id=_uuid(suffix + 200),
        reason="no_match",
        attempted_methods=[ExtractionMethod.DETERMINISTIC],
        created_at=_BASE,
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


def test_completeness_means_entry_stop_and_take_profit_presence():
    measurement = measure_completeness(
        [
            _signal(
                10,
                entry_type=EntryType.MARKET,
                stop_loss="64000",
                take_profits=["67000"],
            ),
            _signal(11, entry_low="65000"),
            _signal(12, stop_loss="64000", take_profits=["67000"]),
        ]
    )

    assert isinstance(measurement, HygieneMeasurement)
    assert measurement.name == "completeness"
    assert measurement.raw_value == pytest.approx(2 / 3)
    assert measurement.normalized == pytest.approx(2 / 3)
    assert measurement.evidence_refs == [
        "signal:00000000-0000-0000-0000-000000000010",
        "signal:00000000-0000-0000-0000-000000000011",
        "signal:00000000-0000-0000-0000-000000000012",
    ]


def test_completeness_excludes_empty_signal_denominator():
    measurement = measure_completeness([])

    assert isinstance(measurement, ExcludedMeasurement)
    assert measurement.name == "completeness"
    assert measurement.note == "completeness: not measured — no extracted signals"


def test_parser_confidence_measures_deterministic_share_of_all_candidates():
    deterministic = _signal(20)
    fallback = _signal(21)
    fallback.extraction_method = ExtractionMethod.LLM_FALLBACK
    measurement = measure_parser_confidence(
        signals=[deterministic, fallback],
        unrecognized=[_unrecognized(22)],
    )

    assert isinstance(measurement, HygieneMeasurement)
    assert measurement.name == "parser_confidence"
    assert measurement.raw_value == pytest.approx(1 / 3)
    assert measurement.normalized == pytest.approx(1 / 3)
    assert measurement.evidence_refs == [
        "signal:00000000-0000-0000-0000-000000000020",
        "signal:00000000-0000-0000-0000-000000000021",
        "unrecognized:00000000-0000-0000-0000-000000000022",
    ]


def test_parser_confidence_keeps_zero_deterministic_as_real_measurement():
    fallback = _signal(23)
    fallback.extraction_method = ExtractionMethod.LLM_FALLBACK
    measurement = measure_parser_confidence(
        signals=[fallback],
        unrecognized=[_unrecognized(24)],
    )

    assert isinstance(measurement, HygieneMeasurement)
    assert measurement.raw_value == 0.0
    assert measurement.normalized == 0.0
    assert measurement.evidence_refs


def test_parser_confidence_excludes_empty_candidate_denominator():
    measurement = measure_parser_confidence(signals=[], unrecognized=[])

    assert isinstance(measurement, ExcludedMeasurement)
    assert measurement.name == "parser_confidence"
    assert measurement.note == "parser_confidence: not measured — no candidates"


def test_evidence_availability_excludes_without_rescan_proof():
    measurement = measure_evidence_availability(
        channel_id=7,
        message_count=10,
        deletions=[],
    )

    assert isinstance(measurement, ExcludedMeasurement)
    assert measurement.name == "evidence_availability"
    assert measurement.note == "evidence_availability: not measured — run rescan"


def test_evidence_availability_penalizes_id_gaps():
    measurement = measure_evidence_availability(
        channel_id=7,
        message_count=9,
        deletions=[_id_gap(30, 10)],
    )

    assert isinstance(measurement, HygieneMeasurement)
    assert measurement.name == "evidence_availability"
    assert measurement.raw_value == pytest.approx(0.9)
    assert measurement.normalized == pytest.approx(0.9)
    assert measurement.evidence_refs == [
        "channel:7",
        "deletion:00000000-0000-0000-0000-000000000030",
    ]


def test_evidence_availability_uses_snapshot_diff_as_clean_rescan_proof():
    measurement = measure_evidence_availability(
        channel_id=7,
        message_count=10,
        deletions=[_deletion(31, 2)],
    )

    assert isinstance(measurement, HygieneMeasurement)
    assert measurement.raw_value == 1.0
    assert measurement.normalized == 1.0
    assert measurement.evidence_refs == [
        "channel:7",
        "deletion:00000000-0000-0000-0000-000000000031",
    ]
