"""Un-weighted hygiene measurements for ProviderScore (ADR 0009)."""

from dataclasses import dataclass, field

from verasig.domain.deletion import DeletedSignalEvidence, DeletionConfidence
from verasig.domain.event import RawSignalEvent


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
