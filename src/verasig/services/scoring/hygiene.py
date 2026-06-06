"""Un-weighted hygiene measurements for ProviderScore (ADR 0009)."""

from dataclasses import dataclass, field


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
