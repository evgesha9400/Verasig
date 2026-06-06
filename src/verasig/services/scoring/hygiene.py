"""Un-weighted hygiene measurements for ProviderScore (ADR 0009)."""

from dataclasses import dataclass, field
from statistics import median
from typing import Protocol

from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.event import RawSignalEvent
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import ExtractedSignal, ExtractionMethod, UnrecognizedSignal
from verasig.domain.simulation import SimOutcome, SimOutcomeKind

ACTIVE_USER_PROXY_ANCHOR = 10_000.0
SIGNAL_FREQUENCY_ANCHOR_PER_DAY = 10.0


class ChannelLike(Protocol):
    channel_id: int
    subscriber_count: int | None


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


def _message_ref(message: RawTelegramMessage) -> str:
    return f"message:{message.channel_id}/{message.message_id}"


def _append_unique(refs: list[str], ref: str) -> None:
    if ref not in refs:
        refs.append(ref)


def _signal_ref(signal: ExtractedSignal) -> str:
    return f"signal:{signal.id}"


def _unrecognized_ref(item: UnrecognizedSignal) -> str:
    return f"unrecognized:{item.id}"


def _outcome_ref(outcome: SimOutcome) -> str:
    return f"signal:{outcome.folded_signal_id}"


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


def _has_r_multiple(outcome: SimOutcome) -> bool:
    return outcome.kind is SimOutcomeKind.R_MULTIPLE and outcome.r_multiple is not None


def _r_multiple_outcomes(outcomes: list[SimOutcome]) -> list[SimOutcome]:
    return [outcome for outcome in outcomes if _has_r_multiple(outcome)]


def _outcome_refs(outcomes: list[SimOutcome]) -> list[str]:
    return [_outcome_ref(outcome) for outcome in outcomes]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _normalize_expectancy(raw_value: float) -> float:
    return _clamp((raw_value + 1.0) / 3.0)


def measure_sim_expectancy(outcomes: list[SimOutcome]) -> Measurement:
    measured = _r_multiple_outcomes(outcomes)
    if not measured:
        return ExcludedMeasurement(
            name="sim_expectancy",
            note="sim_expectancy: pending Slice 9 simulation",
        )
    raw_value = _mean([outcome.r_multiple for outcome in measured])
    return HygieneMeasurement(
        name="sim_expectancy",
        raw_value=raw_value,
        normalized=_normalize_expectancy(raw_value),
        evidence_refs=_outcome_refs(measured),
    )


def measure_drawdown(outcomes: list[SimOutcome]) -> Measurement:
    measured = _r_multiple_outcomes(outcomes)
    if not measured:
        return ExcludedMeasurement(
            name="drawdown",
            note="drawdown: pending Slice 9 simulation",
        )
    raw_value = max(outcome.mae for outcome in measured)
    return HygieneMeasurement(
        name="drawdown",
        raw_value=raw_value,
        normalized=_clamp(1.0 - raw_value),
        evidence_refs=_outcome_refs(measured),
    )


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


def _window_days(messages: list[RawTelegramMessage]) -> float:
    first = min(message.posted_at for message in messages)
    last = max(message.posted_at for message in messages)
    elapsed_days = (last - first).total_seconds() / 86_400
    return max(1.0, elapsed_days)


def _window_boundary_refs(messages: list[RawTelegramMessage]) -> list[str]:
    first = min(messages, key=lambda message: message.posted_at)
    last = max(messages, key=lambda message: message.posted_at)
    refs = [_message_ref(first)]
    if last.message_id != first.message_id or last.channel_id != first.channel_id:
        refs.append(_message_ref(last))
    return refs


def _normalize_signal_frequency(raw_value: float) -> float:
    return min(1.0, raw_value / SIGNAL_FREQUENCY_ANCHOR_PER_DAY)


def measure_signal_frequency(
    events: list[RawSignalEvent],
    messages: list[RawTelegramMessage],
) -> Measurement:
    if not messages:
        return ExcludedMeasurement(
            name="signal_frequency",
            note="signal_frequency: not measured — no captured messages",
        )
    raw_value = len(events) / _window_days(messages)
    refs = [_event_ref(event) for event in events]
    refs.extend(_window_boundary_refs(messages))
    return HygieneMeasurement(
        name="signal_frequency",
        raw_value=raw_value,
        normalized=_normalize_signal_frequency(raw_value),
        evidence_refs=refs,
    )


def _saturate_proxy(value: float) -> float:
    return min(1.0, value / ACTIVE_USER_PROXY_ANCHOR)


def _message_values(
    messages: list[RawTelegramMessage], field_name: str
) -> list[tuple[RawTelegramMessage, int]]:
    return [
        (message, value)
        for message in messages
        if (value := getattr(message, field_name)) is not None
    ]


def _median_value(items: list[tuple[RawTelegramMessage, int]]) -> float:
    return float(median(value for _, value in items))


def _median_refs(items: list[tuple[RawTelegramMessage, int]]) -> list[str]:
    ordered = sorted(items, key=lambda item: item[1])
    count = len(ordered)
    if count == 0:
        return []
    midpoint = count // 2
    if count % 2 == 1:
        return [_message_ref(ordered[midpoint][0])]
    return [_message_ref(ordered[midpoint - 1][0]), _message_ref(ordered[midpoint][0])]


def _proxy_inputs(
    channel: ChannelLike,
    messages: list[RawTelegramMessage],
) -> tuple[list[float], list[str]]:
    values: list[float] = []
    refs = [_channel_ref(channel.channel_id)]
    if channel.subscriber_count is not None:
        values.append(float(channel.subscriber_count))
    for field_name in ["views", "forwards"]:
        items = _message_values(messages, field_name)
        if not items:
            continue
        values.append(_median_value(items))
        for ref in _median_refs(items):
            _append_unique(refs, ref)
    return values, refs


def measure_active_user_proxy(
    channel: ChannelLike,
    messages: list[RawTelegramMessage],
) -> Measurement:
    values, refs = _proxy_inputs(channel, messages)
    if not values:
        return ExcludedMeasurement(
            name="active_user_proxy",
            note="active_user_proxy: not measured — no proxy inputs",
        )
    normalized = sum(_saturate_proxy(value) for value in values) / len(values)
    return HygieneMeasurement(
        name="active_user_proxy",
        raw_value=float(channel.subscriber_count or 0),
        normalized=normalized,
        evidence_refs=refs,
        notes=["active_user_proxy: proxy only, not a quality claim"],
    )
