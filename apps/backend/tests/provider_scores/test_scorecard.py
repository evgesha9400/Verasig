from datetime import datetime, timezone
from uuid import UUID

import pytest

from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.message import RawTelegramMessage
from verasig.domain.score import DEFAULT_WEIGHTS, WEIGHTS_VERSION, ScoreWeights
from verasig.domain.signal import EntryType, Side, Signal
from verasig.domain.simulation import SimOutcome, SimOutcomeKind
from verasig.features.provider_scores.hygiene import (
    ExcludedMeasurement,
    HygieneMeasurement,
)
from verasig.features.provider_scores.scorecard import (
    build_provider_score,
    build_scorecard,
)


def test_default_weights_match_frozen_v0_contract():
    assert WEIGHTS_VERSION == "v0"
    assert DEFAULT_WEIGHTS == ScoreWeights(
        version="v0",
        by_component={
            "sim_expectancy": 0.30,
            "drawdown": 0.20,
            "deletion_behaviour": 0.20,
            "completeness": 0.10,
            "parser_confidence": 0.10,
            "evidence_availability": 0.10,
            "signal_frequency": 0.0,
            "active_user_proxy": 0.0,
        },
    )


def _computed_at() -> datetime:
    return datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _uuid(suffix: int) -> UUID:
    return UUID(f"10000000-0000-0000-0000-{suffix:012d}")


def _channel() -> TelegramChannel:
    return TelegramChannel(
        channel_id=7,
        handle="pilot",
        title="Pilot",
        is_private=False,
        subscriber_count=1000,
        first_seen_at=_computed_at(),
    )


def _message(message_id: int) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=7,
        message_id=message_id,
        posted_at=_computed_at(),
        captured_at=_computed_at(),
        has_media=False,
        raw_payload={"id": message_id},
    )


def _signal(suffix: int, message_id: int) -> Signal:
    return Signal(
        id=_uuid(suffix),
        channel_id=7,
        message_id=message_id,
        candidate_text="BTC long",
        symbol="BTC",
        side=Side.LONG,
        entry_type=EntryType.MARKET,
        stop_loss="64000",
        take_profits=["67000"],
        extracted_at=_computed_at(),
    )


def _snapshot_rescan_proof(suffix: int) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        id=_uuid(suffix),
        channel_id=7,
        message_id=99,
        confidence=DeletionConfidence.CONFIRMED,
        method=DeletionMethod.SNAPSHOT_DIFF,
        detected_at=_computed_at(),
        was_signal_candidate=False,
    )


def _sim_outcome(signal: Signal) -> SimOutcome:
    return SimOutcome(
        folded_signal_id=signal.id,
        kind=SimOutcomeKind.R_MULTIPLE,
        r_multiple=2.0,
        mfe=2.0,
        mae=0.25,
        entry_fill_at=_computed_at(),
        exit_at=_computed_at(),
        exit_reason="tp",
        policy="ProviderStatedPolicy",
        tie_break="stop_first",
    )


def test_scorecard_applies_weights_without_renormalizing():
    score, explanation = build_scorecard(
        channel_id=7,
        signal_count=3,
        computed_at=_computed_at(),
        measurements=[
            HygieneMeasurement(
                name="deletion_behaviour",
                raw_value=0.5,
                normalized=0.5,
                evidence_refs=["event:aaaaaaaa-0000-0000-0000-000000000000"],
            ),
            HygieneMeasurement(
                name="completeness",
                raw_value=1.0,
                normalized=1.0,
                evidence_refs=["signal:bbbbbbbb-0000-0000-0000-000000000000"],
            ),
            HygieneMeasurement(
                name="signal_frequency",
                raw_value=2.0,
                normalized=1.0,
                evidence_refs=[
                    "event:cccccccc-0000-0000-0000-000000000000",
                    "message:7/1",
                    "message:7/3",
                ],
            ),
        ],
    )

    assert score.channel_id == 7
    assert score.score == 0.2
    assert score.signal_count == 3
    assert score.simulated_count == 0
    assert score.computed_at == _computed_at()
    assert score.weights_version == "v0"
    assert [component.name for component in score.components] == [
        "deletion_behaviour",
        "completeness",
        "signal_frequency",
    ]
    assert [component.contribution for component in score.components] == [
        0.1,
        0.1,
        0.0,
    ]
    assert score.components[2].weight == 0.0
    assert explanation.channel_id == score.channel_id
    assert explanation.score == score.score
    assert explanation.breakdown == score.components
    assert "sim_expectancy: simulation not supplied" in explanation.notes
    assert "drawdown: simulation not supplied" in explanation.notes


def test_scorecard_excludes_empty_denominator_measurements_with_note():
    score, explanation = build_scorecard(
        channel_id=7,
        signal_count=0,
        computed_at=_computed_at(),
        measurements=[
            ExcludedMeasurement(
                name="completeness",
                note="completeness: not measured — no extracted signals",
            )
        ],
    )

    assert score.components == []
    assert score.score == 0
    assert explanation.breakdown == []
    assert "completeness: not measured — no extracted signals" in explanation.notes


def test_scorecard_reweights_measurements_deterministically():
    base_score, _ = build_scorecard(
        channel_id=7,
        signal_count=1,
        computed_at=_computed_at(),
        measurements=[
            HygieneMeasurement(
                name="deletion_behaviour",
                raw_value=0.5,
                normalized=0.5,
                evidence_refs=["event:aaaaaaaa-0000-0000-0000-000000000000"],
            )
        ],
    )
    custom_score, _ = build_scorecard(
        channel_id=7,
        signal_count=1,
        computed_at=_computed_at(),
        measurements=[
            HygieneMeasurement(
                name="deletion_behaviour",
                raw_value=0.5,
                normalized=0.5,
                evidence_refs=["event:aaaaaaaa-0000-0000-0000-000000000000"],
            )
        ],
        weights=ScoreWeights(version="test", by_component={"deletion_behaviour": 0.8}),
    )

    assert base_score.score == 0.1
    assert custom_score.score == 0.4
    assert custom_score.weights_version == "test"


def test_provider_score_builder_measures_all_present_components():
    signal = _signal(2, 10)
    score, explanation = build_provider_score(
        channel=_channel(),
        messages=[_message(10), _message(11)],
        message_count=2,
        events=[signal],
        signals=[signal],
        missed_event_ids=[],
        deletions=[_snapshot_rescan_proof(3)],
        computed_at=_computed_at(),
    )

    assert score.signal_count == 1
    assert score.simulated_count == 0
    assert [component.name for component in score.components] == [
        "deletion_behaviour",
        "completeness",
        "parser_confidence",
        "evidence_availability",
        "signal_frequency",
        "active_user_proxy",
    ]
    assert score.score == 0.5
    assert explanation.breakdown == score.components


def test_provider_score_builder_adds_simulation_components_when_outcomes_exist():
    signal = _signal(5, 10)
    score, explanation = build_provider_score(
        channel=_channel(),
        messages=[_message(10), _message(11)],
        message_count=2,
        events=[signal],
        signals=[signal],
        missed_event_ids=[],
        deletions=[_snapshot_rescan_proof(6)],
        sim_outcomes=[_sim_outcome(signal)],
        computed_at=_computed_at(),
    )

    assert score.simulated_count == 1
    assert [component.name for component in score.components[:2]] == [
        "sim_expectancy",
        "drawdown",
    ]
    assert score.components[0].normalized == 1.0
    assert score.components[0].contribution == pytest.approx(0.30)
    assert score.components[1].normalized == 0.75
    assert score.components[1].contribution == pytest.approx(0.15)
    assert score.score == pytest.approx(0.95)
    assert "sim_expectancy: simulation not supplied" not in explanation.notes
    assert "drawdown: simulation not supplied" not in explanation.notes
