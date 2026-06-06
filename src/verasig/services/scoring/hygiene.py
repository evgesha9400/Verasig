"""Un-weighted hygiene measurements for ProviderScore (ADR 0009)."""

from dataclasses import dataclass, field

from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.event import RawSignalEvent
from verasig.domain.signal import ExtractedSignal, ExtractionMethod, UnrecognizedSignal


@dataclass(frozen=True)
class HygieneMeasurement:
    name: str
    raw_value: float
    normalized: float
    evidence_refs: list[str]
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExcludedMeasurement:
    name: str
    note: str


Measurement = HygieneMeasurement | ExcludedMeasurement


def _event_ref(event: RawSignalEvent) -> str:
    return f"event:{event.id}"


def _deletion_ref(evidence: DeletedSignalEvidence) -> str:
    return f"deletion:{evidence.id}"


def _channel_ref(channel_id: int) -> str:
    return f"channel:{channel_id}"


def _signal_ref(signal: ExtractedSignal) -> str:
    return f"signal:{signal.id}"


def _unrecognized_ref(item: UnrecognizedSignal) -> str:
    return f"unrecognized:{item.id}"


def _is_confirmed_signal_deletion(evidence: DeletedSignalEvidence) -> bool:
    return (
        evidence.confidence is DeletionConfidence.CONFIRMED
        and evidence.was_signal_candidate
    )


def _confirmed_signal_deletions(
    deletions: list[DeletedSignalEvidence],
) -> list[DeletedSignalEvidence]:
    return [item for item in deletions if _is_confirmed_signal_deletion(item)]


def measure_deletion_behaviour(
    events: list[RawSignalEvent],
    deletions: list[DeletedSignalEvidence],
) -> Measurement:
    if not events:
        return ExcludedMeasurement(
            name="deletion_behaviour",
            note="deletion_behaviour: not measured — no signal candidates",
        )
    signal_deletions = _confirmed_signal_deletions(deletions)
    deletion_rate = len(signal_deletions) / len(events)
    value = 1 - deletion_rate
    refs = [_deletion_ref(item) for item in signal_deletions]
    refs.extend(_event_ref(event) for event in events)
    return HygieneMeasurement(
        name="deletion_behaviour",
        raw_value=value,
        normalized=value,
        evidence_refs=refs,
    )


def _has_entry(signal: ExtractedSignal) -> bool:
    return signal.entry_type is not None or signal.entry_low is not None


def _has_stop(signal: ExtractedSignal) -> bool:
    return signal.stop_loss is not None


def _has_take_profit(signal: ExtractedSignal) -> bool:
    return len(signal.take_profits) > 0


def _completion_ratio(signal: ExtractedSignal) -> float:
    present = sum(
        [
            _has_entry(signal),
            _has_stop(signal),
            _has_take_profit(signal),
        ]
    )
    return present / 3


def measure_completeness(signals: list[ExtractedSignal]) -> Measurement:
    if not signals:
        return ExcludedMeasurement(
            name="completeness",
            note="completeness: not measured — no extracted signals",
        )
    value = sum(_completion_ratio(signal) for signal in signals) / len(signals)
    return HygieneMeasurement(
        name="completeness",
        raw_value=value,
        normalized=value,
        evidence_refs=[_signal_ref(signal) for signal in signals],
    )


def _is_deterministic(signal: ExtractedSignal) -> bool:
    return signal.extraction_method is ExtractionMethod.DETERMINISTIC


def measure_parser_confidence(
    signals: list[ExtractedSignal],
    unrecognized: list[UnrecognizedSignal],
) -> Measurement:
    total = len(signals) + len(unrecognized)
    if total == 0:
        return ExcludedMeasurement(
            name="parser_confidence",
            note="parser_confidence: not measured — no candidates",
        )
    deterministic = sum(1 for signal in signals if _is_deterministic(signal))
    value = deterministic / total
    refs = [_signal_ref(signal) for signal in signals]
    refs.extend(_unrecognized_ref(item) for item in unrecognized)
    return HygieneMeasurement(
        name="parser_confidence",
        raw_value=value,
        normalized=value,
        evidence_refs=refs,
    )


def _is_rescan_proof(evidence: DeletedSignalEvidence) -> bool:
    return evidence.method in {
        DeletionMethod.SNAPSHOT_DIFF,
        DeletionMethod.ID_GAP,
    }


def _id_gap_deletions(
    deletions: list[DeletedSignalEvidence],
) -> list[DeletedSignalEvidence]:
    return [item for item in deletions if item.method is DeletionMethod.ID_GAP]


def _snapshot_diff_deletions(
    deletions: list[DeletedSignalEvidence],
) -> list[DeletedSignalEvidence]:
    return [item for item in deletions if item.method is DeletionMethod.SNAPSHOT_DIFF]


def _evidence_availability_refs(
    channel_id: int,
    id_gaps: list[DeletedSignalEvidence],
    snapshot_diffs: list[DeletedSignalEvidence],
) -> list[str]:
    refs = [_channel_ref(channel_id)]
    if id_gaps:
        refs.extend(_deletion_ref(item) for item in id_gaps)
        return refs
    refs.extend(_deletion_ref(item) for item in snapshot_diffs)
    return refs


def measure_evidence_availability(
    channel_id: int,
    message_count: int,
    deletions: list[DeletedSignalEvidence],
) -> Measurement:
    proof = [item for item in deletions if _is_rescan_proof(item)]
    if not proof:
        return ExcludedMeasurement(
            name="evidence_availability",
            note="evidence_availability: not measured — run rescan",
        )
    id_gaps = _id_gap_deletions(proof)
    denominator = message_count + len(id_gaps)
    if denominator == 0:
        return ExcludedMeasurement(
            name="evidence_availability",
            note="evidence_availability: not measured — no captured messages or gaps",
        )
    value = message_count / denominator
    return HygieneMeasurement(
        name="evidence_availability",
        raw_value=value,
        normalized=value,
        evidence_refs=_evidence_availability_refs(
            channel_id, id_gaps, _snapshot_diff_deletions(proof)
        ),
    )
