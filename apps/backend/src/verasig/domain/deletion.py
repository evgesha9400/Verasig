"""Deletion-evidence contract (data-contracts.md §6; ADR 0008).

`DeletedSignalEvidence` is a durable, NON-recomputable projection: a deletion is
observed against an ephemeral live re-fetch that nothing retains, so the
observation itself is the only honest record. Coupling: `SNAPSHOT_DIFF→CONFIRMED`
(content retained), `ID_GAP→SUSPECTED` (no content), `LIVE_EVENT→CONFIRMED`
for realtime delete notices. `detected_at` defaults to `_now()` but the detector
injects it for deterministic tests.
"""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DeletionConfidence(StrEnum):
    CONFIRMED = "CONFIRMED"
    SUSPECTED = "SUSPECTED"


class DeletionMethod(StrEnum):
    SNAPSHOT_DIFF = "SNAPSHOT_DIFF"
    ID_GAP = "ID_GAP"
    LIVE_EVENT = "LIVE_EVENT"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class DeletedSignalEvidence(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    channel_id: int
    message_id: int
    confidence: DeletionConfidence  # CONFIRMED | SUSPECTED
    method: DeletionMethod  # SNAPSHOT_DIFF | ID_GAP | LIVE_EVENT
    original_text: str | None = None  # retained iff CONFIRMED/LIVE_EVENT
    first_seen_at: datetime | None = None  # the stored captured_at, when CONFIRMED
    detected_at: datetime = Field(default_factory=_now)
    was_signal_candidate: bool  # was a RawSignalEvent?
