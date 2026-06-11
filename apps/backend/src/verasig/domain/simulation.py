"""Simulation contracts (data-contracts.md §8; ADR 0003)."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class SimOutcomeKind(StrEnum):
    R_MULTIPLE = "R_MULTIPLE"
    MARK_TO_MARKET = "MARK_TO_MARKET"
    UNFILLED = "UNFILLED"


class SimOutcome(BaseModel):
    folded_signal_id: UUID
    kind: SimOutcomeKind
    r_multiple: float | None = None
    pct_return: float | None = None
    mfe: float
    mae: float
    entry_fill_at: datetime | None = None
    exit_at: datetime | None = None
    exit_reason: str
    policy: str
    tie_break: str


class Kline(BaseModel):
    symbol: str
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
