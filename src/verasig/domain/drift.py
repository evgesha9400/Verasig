"""Drift records — false-negative evidence for the next distillation (§1, §4).

A `FilterDriftWarning` records a candidate-filter miss (a message that later
proved a signal; found by background parse, operator audit, or the LLM). A
`ParserDriftWarning` records a deterministic-parser miss that the LLM fallback
then extracted. Both surface false negatives so each becomes a labeled example
for the next distillation (ADR 0005, 0006).
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


class ParserDriftWarning(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    event_id: UUID  # → RawSignalEvent the deterministic parser did not extract
    channel_id: int
    deterministic_result: str = "no_match"
    fallback_result: str = "extracted"
    fallback_signal_id: UUID  # the ExtractedSignal the fallback produced
    created_at: datetime = Field(default_factory=_now)
