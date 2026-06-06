"""Un-weighted hygiene measurements for ProviderScore (ADR 0009)."""

from dataclasses import dataclass, field

from verasig.domain.deletion import DeletedSignalEvidence, DeletionConfidence
from verasig.domain.event import RawSignalEvent
from verasig.domain.signal import ExtractedSignal


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


def _signal_ref(signal: ExtractedSignal) -> str:
    return f"signal:{signal.id}"


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
