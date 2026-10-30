from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class EntryMode(StrEnum):
    FIRST = "first"
    MID = "mid"
    LADDER = "ladder"


class Weighting(StrEnum):
    EQUAL = "equal"
    MARTINGALE = "martingale"


class ExitSource(StrEnum):
    SIGNAL = "signal"
    CUSTOM = "custom"


@dataclass(frozen=True)
class RiskConfig:
    entry_mode: EntryMode = EntryMode.MID
    levels: int = 3
    weighting: Weighting = Weighting.EQUAL
    exit_source: ExitSource = ExitSource.SIGNAL
    stop_pct: Decimal = Decimal("2.5")
    tp_pct: Decimal = Decimal("7.5")
    risk_pct: Decimal = Decimal("2.0")
    leverage: int = 5
