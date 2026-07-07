"""Advisory candidate-event contracts (data-contracts.md §1, §2; ADR 0005).

`RawSignalEvent` is the ADVISORY signal candidate — priority/triage, not a hard
gate. It may be late-materialized (a background parse or audit finds a missed
signal), so `materialized_by` records how it was flagged.
"""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MaterializationPath(StrEnum):
    SEED_HEURISTIC = "SEED_HEURISTIC"
    FILTER_RULE = "FILTER_RULE"
    PARSER_BACKFILL = "PARSER_BACKFILL"
    HUMAN_AUDIT = "HUMAN_AUDIT"
    MINING = "MINING"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class RawSignalEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    channel_id: int
    message_id: int  # (channel_id, message_id) unique
    candidate_text: str  # exact slice fed to extraction (verbatim message text)
    materialized_by: MaterializationPath
    created_at: datetime = Field(default_factory=_now)
