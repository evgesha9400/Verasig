"""Extraction contracts (data-contracts.md §1, §3).

`ExtractedSignal` is the canonical parsed trade intent (required = symbol + side);
`UnrecognizedSignal` is the evidence-of-a-gap outcome when extraction fails.
Construction-friendly defaults let the parser build a signal from a
`RawSignalEvent` + matched fields; the linkage (`event_id`, `channel_id`) is
always supplied by the caller, which holds the event.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


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
    UNRECOGNIZED = "UNRECOGNIZED"


class ExtractionMethod(StrEnum):
    DETERMINISTIC = "DETERMINISTIC"
    LLM_FALLBACK = "LLM_FALLBACK"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ExtractedSignal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    event_id: UUID
    channel_id: int
    symbol: str
    side: Side
    event_type: SignalEventType = SignalEventType.NEW_ENTRY
    references_message_id: int | None = None
    entry_type: EntryType | None = None
    entry_low: Decimal | None = None
    entry_high: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profits: list[Decimal] = Field(default_factory=list)
    leverage: Decimal | None = None
    confidence: Decimal | None = None
    parser_confidence: float = 1.0
    extraction_method: ExtractionMethod = ExtractionMethod.DETERMINISTIC
    rule_id: str | None = None
    extracted_at: datetime = Field(default_factory=_now)

    @model_validator(mode="after")
    def _require_symbol_and_side(self) -> "ExtractedSignal":
        if not self.symbol:
            raise ValueError("symbol is required")
        return self


class UnrecognizedSignal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    event_id: UUID
    reason: str  # no_symbol | no_side | no_match | fallback_failed
    attempted_methods: list[ExtractionMethod] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
