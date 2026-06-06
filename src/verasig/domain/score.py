"""Provider score contracts (data-contracts.md §7; ADR 0009)."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

WEIGHTS_VERSION = "v0"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ScoreComponent(BaseModel):
    name: str
    raw_value: float
    normalized: float
    weight: float
    contribution: float
    evidence_refs: list[str]


class ProviderScore(BaseModel):
    channel_id: int
    score: float
    components: list[ScoreComponent]
    signal_count: int
    simulated_count: int
    computed_at: datetime = Field(default_factory=_now)
    weights_version: str


class ProviderScoreExplanation(BaseModel):
    channel_id: int
    score: float
    breakdown: list[ScoreComponent]
    notes: list[str]


class ScoreWeights(BaseModel):
    version: str
    by_component: dict[str, float]


DEFAULT_WEIGHTS = ScoreWeights(
    version=WEIGHTS_VERSION,
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
