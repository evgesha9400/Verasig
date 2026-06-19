"""Operator ground-truth label — the golden corpus (data-contracts.md §4).

A `GoldenLabel` is the operator's verdict on one message: `label`, plus the
`expected` `ExtractedSignal` fields when positive. The labeled set is the
precision/recall oracle and the provenance both rule kinds are distilled from.
"""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from verasig.domain.signal import ExtractedSignal


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class LabelKind(StrEnum):
    SIGNAL = "signal"
    NOISE = "noise"
    MODIFIER = "modifier"


class GoldenLabel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID | None = None
    channel_id: int
    message_id: int
    label: LabelKind
    expected: ExtractedSignal | None = None
    labeled_at: datetime = Field(default_factory=_now)

    @property
    def is_signal(self) -> bool:
        return self.label == LabelKind.SIGNAL


class DistillationExample(GoldenLabel):
    text: str | None = None
