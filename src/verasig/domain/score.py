"""Provider score contracts (data-contracts.md §7; ADR 0009)."""

from pydantic import BaseModel

WEIGHTS_VERSION = "v0"


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
