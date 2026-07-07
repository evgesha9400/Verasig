"""Extraction contracts (data-contracts.md §1, §3).

`TradeIntent` is the provenance-free parsed trade (required = symbol + side);
the deterministic extractor emits it from text alone, and the symbol is
normalized here so callers get it for free. `Signal` extends `TradeIntent`
with the linkage/provenance of the candidate message it was extracted from
(`channel_id`, `message_id`, `candidate_text`, `rule_id`) — one row per
message, since the miner is the only extractor and every persisted signal IS
an extraction (there are no stored "misses").
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class EntryType(StrEnum):
    MARKET = "MARKET"
    LIMIT_SINGLE = "LIMIT_SINGLE"
    LIMIT_RANGE = "LIMIT_RANGE"


class SignalEventType(StrEnum):
    NEW_ENTRY = "NEW_ENTRY"
    MODIFY = "MODIFY"
    CLOSE = "CLOSE"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TradeIntent(BaseModel):
    symbol: str
    side: Side
    entry_type: EntryType | None = None
    entry_low: Decimal | None = None
    entry_high: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profits: list[Decimal] = Field(default_factory=list)
    leverage: Decimal | None = None
    confidence: Decimal | None = None

    @field_validator("symbol")
    @classmethod
    def _normalize_symbol(cls, raw: str) -> str:
        symbol = raw.strip().upper()
        if symbol and not symbol.endswith("USDT"):
            return f"{symbol}USDT"
        return symbol

    @model_validator(mode="after")
    def _require_symbol(self) -> "TradeIntent":
        if not self.symbol:
            raise ValueError("symbol is required")
        return self


class Signal(TradeIntent):
    id: UUID = Field(default_factory=uuid4)
    channel_id: int
    message_id: int  # (channel_id, message_id) unique — one signal per message
    candidate_text: str  # exact slice fed to extraction (verbatim message text)
    event_type: SignalEventType = SignalEventType.NEW_ENTRY
    rule_id: str | None = None
    extracted_at: datetime = Field(default_factory=_now)
