"""Weighted ProviderScore assembly (ADR 0009)."""

from datetime import datetime

from verasig.domain.score import (
    DEFAULT_WEIGHTS,
    ProviderScore,
    ProviderScoreExplanation,
    ScoreComponent,
    ScoreWeights,
)
from verasig.services.scoring.hygiene import HygieneMeasurement

_PENDING_SIM_NOTES = [
    "sim_expectancy: pending Slice 9 simulation",
    "drawdown: pending Slice 9 simulation",
]


def _component_weight(measurement: HygieneMeasurement, weights: ScoreWeights) -> float:
    return weights.by_component.get(measurement.name, 0.0)


def _score_component(
    measurement: HygieneMeasurement, weights: ScoreWeights
) -> ScoreComponent:
    weight = _component_weight(measurement, weights)
    return ScoreComponent(
        name=measurement.name,
        raw_value=measurement.raw_value,
        normalized=measurement.normalized,
        weight=weight,
        contribution=measurement.normalized * weight,
        evidence_refs=measurement.evidence_refs,
    )


def _score_components(
    measurements: list[HygieneMeasurement], weights: ScoreWeights
) -> list[ScoreComponent]:
    return [_score_component(measurement, weights) for measurement in measurements]


def _score_value(components: list[ScoreComponent]) -> float:
    return sum(component.contribution for component in components)


def _notes(measurements: list[HygieneMeasurement]) -> list[str]:
    notes = list(_PENDING_SIM_NOTES)
    for measurement in measurements:
        notes.extend(measurement.notes)
    return notes


def build_scorecard(
    channel_id: int,
    signal_count: int,
    computed_at: datetime,
    measurements: list[HygieneMeasurement],
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> tuple[ProviderScore, ProviderScoreExplanation]:
    """Build ProviderScore + ProviderScoreExplanation from un-weighted metrics."""
    components = _score_components(measurements, weights)
    score_value = _score_value(components)
    score = ProviderScore(
        channel_id=channel_id,
        score=score_value,
        components=components,
        signal_count=signal_count,
        simulated_count=0,
        computed_at=computed_at,
        weights_version=weights.version,
    )
    explanation = ProviderScoreExplanation(
        channel_id=channel_id,
        score=score_value,
        breakdown=components,
        notes=_notes(measurements),
    )
    return score, explanation
