from decimal import Decimal

from pydantic import Field

from verasig.api.schemas.common import CamelModel
from verasig.domain.risk_config import EntryMode, ExitSource, RiskConfig, Weighting


class RiskConfigBody(CamelModel):
    entry_mode: EntryMode = EntryMode.MID
    levels: int = Field(default=3, ge=2, le=5)
    weighting: Weighting = Weighting.EQUAL
    exit_source: ExitSource = ExitSource.SIGNAL
    stop_pct: Decimal = Decimal("2.5")
    tp_pct: Decimal = Decimal("7.5")
    risk_pct: Decimal = Decimal("2.0")
    leverage: int = 5


def to_body(config: RiskConfig) -> RiskConfigBody:
    return RiskConfigBody(
        entry_mode=config.entry_mode,
        levels=config.levels,
        weighting=config.weighting,
        exit_source=config.exit_source,
        stop_pct=config.stop_pct,
        tp_pct=config.tp_pct,
        risk_pct=config.risk_pct,
        leverage=config.leverage,
    )


def to_config(payload: RiskConfigBody) -> RiskConfig:
    return RiskConfig(
        entry_mode=payload.entry_mode,
        levels=payload.levels,
        weighting=payload.weighting,
        exit_source=payload.exit_source,
        stop_pct=payload.stop_pct,
        tp_pct=payload.tp_pct,
        risk_pct=payload.risk_pct,
        leverage=payload.leverage,
    )
