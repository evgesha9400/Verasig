"""Signal-lifecycle folded view (data-contracts.md §5; ADR 0007).

A `FoldedSignal` is the time-ordered timeline of an entry plus the modifications
in its reply chain — the effective stop, take-profits, position size and average
entry after each step. Derived + recomputable, never stored; `fold_version` pins
the lifecycle logic so a past fold is reproducible. Modifications are recognized
from `reply_to` (not the parser), so a step's source is the durable
`source_message_id`; `source_signal_id` stays the entry's `root_signal_id`.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from verasig.domain.signal import Side, SignalEventType

FOLD_VERSION = 1


class FoldStep(BaseModel):
    at: datetime  # source message's posted_at (true timeline)
    source_signal_id: UUID  # = root_signal_id (durable entry signal)
    source_message_id: int  # the message that caused this step
    event_type: SignalEventType  # NEW_ENTRY | MODIFY | CLOSE
    effective_stop_loss: Decimal | None = None
    effective_take_profits: list[Decimal] = Field(default_factory=list)
    effective_size: Decimal  # cumulative (entry = 1; multipliers stated)
    effective_entry: Decimal | None = None  # size-weighted avg of PRICED legs
    entry_low: Decimal | None = None  # original entry range low, if available
    entry_high: Decimal | None = None  # original entry range high, if available
    leg_size: Decimal | None = None  # this step's size delta (+add / −reduce)
    leg_price: Decimal | None = None  # this step's leg price; None ⇒ market-at-`at`


class FoldedSignal(BaseModel):
    root_signal_id: UUID  # the NEW_ENTRY Signal id
    symbol: str
    side: Side
    timeline: list[FoldStep]  # time-ordered by posted_at
    closed_at: datetime | None = None  # set when CLOSE applied or effective_size → 0
    fold_version: int = FOLD_VERSION
