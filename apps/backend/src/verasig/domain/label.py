"""Operator ground-truth label — the golden corpus (data-contracts.md §4).

A `GoldenLabel` is the operator's verdict on one message: `is_signal`, plus the
`expected` `ExtractedSignal` fields when positive. The labeled set is the
precision/recall oracle (filter recall on `is_signal`, parser precision on
`expected`) and the provenance both rule kinds are distilled from.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from verasig.domain.signal import ExtractedSignal


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class GoldenLabel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    channel_id: int
    message_id: int
    is_signal: bool
    expected: ExtractedSignal | None = None  # expected fields when is_signal
    labeled_at: datetime = Field(default_factory=_now)
