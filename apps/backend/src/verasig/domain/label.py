"""Operator ground-truth label — the golden corpus (data-contracts.md §4).

A `GoldenLabel` is the operator's verdict on one message: `is_signal`, plus the
`expected` `ExtractedSignal` fields when positive. The labeled set is the
precision/recall oracle (filter recall on `is_signal`, parser precision on
`expected`) and the provenance both rule kinds are distilled from.
"""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

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
    expected: ExtractedSignal | None = None  # expected fields when is_signal
    labeled_at: datetime = Field(default_factory=_now)

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_is_signal(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "label" in data or "is_signal" not in data:
            return data
        label = LabelKind.SIGNAL if data["is_signal"] else LabelKind.NOISE
        return {**data, "label": label}

    @property
    def is_signal(self) -> bool:
        return self.label is LabelKind.SIGNAL
