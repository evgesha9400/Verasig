from datetime import datetime, timezone

from verasig.domain.score import DEFAULT_WEIGHTS, WEIGHTS_VERSION, ScoreWeights


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
