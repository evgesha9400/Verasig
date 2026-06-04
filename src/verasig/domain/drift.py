"""Candidate-filter false-negative record (data-contracts.md §1, §4; ADR 0005).

A `FilterDriftWarning` is emitted whenever the candidate filter missed a message
that later proved to be a signal — found by a background deterministic parse, an
operator audit, or the LLM. Surfaces filter false negatives so each becomes a
labeled example for the next distillation; symmetric to `ParserDriftWarning`.
"""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MissDiscoveredBy(StrEnum):
    PARSER_BACKFILL = "PARSER_BACKFILL"
    HUMAN_AUDIT = "HUMAN_AUDIT"
    LLM_FALLBACK = "LLM_FALLBACK"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class FilterDriftWarning(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    channel_id: int
    message_id: int  # → RawTelegramMessage the filter did not flag
    filter_rule_version: int | None = None  # null = seed heuristic
    miss_discovered_by: MissDiscoveredBy
    event_id: UUID | None = None  # the late-materialized RawSignalEvent, if any
    source_label_id: UUID | None = None  # the GoldenLabel that proved it, if any
    created_at: datetime = Field(default_factory=_now)
