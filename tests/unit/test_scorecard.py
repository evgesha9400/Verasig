from datetime import datetime, timezone

from verasig.domain.score import DEFAULT_WEIGHTS, WEIGHTS_VERSION, ScoreWeights
from verasig.services.scoring.hygiene import ExcludedMeasurement, HygieneMeasurement
from verasig.services.scoring.scorecard import build_scorecard


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
    assert "sim_expectancy: pending Slice 9 simulation" in explanation.notes
    assert "drawdown: pending Slice 9 simulation" in explanation.notes


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
