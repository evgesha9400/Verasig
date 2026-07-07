"""Weighted ProviderScore assembly (ADR 0009)."""

from datetime import datetime
from uuid import UUID

from verasig.domain.deletion import DeletedSignalEvidence
from verasig.domain.event import RawSignalEvent
from verasig.domain.message import RawTelegramMessage
from verasig.domain.score import (
    DEFAULT_WEIGHTS,
    ProviderScore,
    ProviderScoreExplanation,
    ScoreComponent,
    ScoreWeights,
)
from verasig.domain.signal import ExtractedSignal
from verasig.domain.simulation import SimOutcome, SimOutcomeKind
from verasig.features.provider_scores.hygiene import (
    ChannelLike,
    ExcludedMeasurement,
    HygieneMeasurement,
    Measurement,
    measure_active_user_proxy,
    measure_completeness,
    measure_deletion_behaviour,
    measure_drawdown,
    measure_evidence_availability,
    measure_parser_confidence,
    measure_signal_frequency,
    measure_sim_expectancy,
)

_SIM_NOTES_BY_COMPONENT = {
    "sim_expectancy": "sim_expectancy: simulation not supplied",
    "drawdown": "drawdown: simulation not supplied",
}


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
    measurements: list[Measurement], weights: ScoreWeights
) -> list[ScoreComponent]:
    return [
        _score_component(measurement, weights)
        for measurement in measurements
        if isinstance(measurement, HygieneMeasurement)
    ]


def _score_value(components: list[ScoreComponent]) -> float:
    return sum(component.contribution for component in components)


def _measurement_notes(measurement: Measurement) -> list[str]:
    if isinstance(measurement, ExcludedMeasurement):
        return [measurement.note]
    return measurement.notes


def _missing_sim_notes(measurements: list[Measurement]) -> list[str]:
    names = {measurement.name for measurement in measurements}
    return [note for name, note in _SIM_NOTES_BY_COMPONENT.items() if name not in names]


def _notes(measurements: list[Measurement]) -> list[str]:
    notes = _missing_sim_notes(measurements)
    for measurement in measurements:
        notes.extend(_measurement_notes(measurement))
    return notes


def _is_simulated(outcome: SimOutcome) -> bool:
    return outcome.kind is not SimOutcomeKind.UNFILLED


def _simulated_count(outcomes: list[SimOutcome]) -> int:
    return sum(1 for outcome in outcomes if _is_simulated(outcome))


def build_scorecard(
    channel_id: int,
    signal_count: int,
    computed_at: datetime,
    measurements: list[Measurement],
    simulated_count: int = 0,
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
        simulated_count=simulated_count,
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


def _measurements(
    channel: ChannelLike,
    messages: list[RawTelegramMessage],
    message_count: int,
    events: list[RawSignalEvent],
    signals: list[ExtractedSignal],
    missed_event_ids: list[UUID],
    deletions: list[DeletedSignalEvidence],
    sim_outcomes: list[SimOutcome],
) -> list[Measurement]:
    return [
        measure_sim_expectancy(sim_outcomes),
        measure_drawdown(sim_outcomes),
        measure_deletion_behaviour(events, deletions),
        measure_completeness(signals),
        measure_parser_confidence(signals, missed_event_ids),
        measure_evidence_availability(channel.channel_id, message_count, deletions),
        measure_signal_frequency(events, messages),
        measure_active_user_proxy(channel, messages),
    ]


def build_provider_score(
    channel: ChannelLike,
    messages: list[RawTelegramMessage],
    message_count: int,
    events: list[RawSignalEvent],
    signals: list[ExtractedSignal],
    missed_event_ids: list[UUID],
    deletions: list[DeletedSignalEvidence],
    computed_at: datetime,
    sim_outcomes: list[SimOutcome] | None = None,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> tuple[ProviderScore, ProviderScoreExplanation]:
    """Build a scorecard from durable channel inputs."""
    outcomes = [] if sim_outcomes is None else sim_outcomes
    return build_scorecard(
        channel_id=channel.channel_id,
        signal_count=len(signals),
        computed_at=computed_at,
        measurements=_measurements(
            channel,
            messages,
            message_count,
            events,
            signals,
            missed_event_ids,
            deletions,
            outcomes,
        ),
        simulated_count=_simulated_count(outcomes),
        weights=weights,
    )
