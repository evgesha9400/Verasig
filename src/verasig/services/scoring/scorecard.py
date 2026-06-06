"""Weighted ProviderScore assembly (ADR 0009)."""

from datetime import datetime

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
from verasig.domain.signal import ExtractedSignal, UnrecognizedSignal
from verasig.services.scoring.hygiene import (
    ChannelLike,
    ExcludedMeasurement,
    HygieneMeasurement,
    Measurement,
    measure_active_user_proxy,
    measure_completeness,
    measure_deletion_behaviour,
    measure_evidence_availability,
    measure_parser_confidence,
    measure_signal_frequency,
)

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


def _notes(measurements: list[Measurement]) -> list[str]:
    notes = list(_PENDING_SIM_NOTES)
    for measurement in measurements:
        notes.extend(_measurement_notes(measurement))
    return notes


def build_scorecard(
    channel_id: int,
    signal_count: int,
    computed_at: datetime,
    measurements: list[Measurement],
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


def _measurements(
    channel: ChannelLike,
    messages: list[RawTelegramMessage],
    message_count: int,
    events: list[RawSignalEvent],
    signals: list[ExtractedSignal],
    unrecognized: list[UnrecognizedSignal],
    deletions: list[DeletedSignalEvidence],
) -> list[Measurement]:
    return [
        measure_deletion_behaviour(events, deletions),
        measure_completeness(signals),
        measure_parser_confidence(signals, unrecognized),
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
    unrecognized: list[UnrecognizedSignal],
    deletions: list[DeletedSignalEvidence],
    computed_at: datetime,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> tuple[ProviderScore, ProviderScoreExplanation]:
    """Build the Slice-8 scorecard from durable channel inputs."""
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
            unrecognized,
            deletions,
        ),
        weights=weights,
    )
