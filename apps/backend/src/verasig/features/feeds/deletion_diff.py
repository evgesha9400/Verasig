"""Pure deletion detector (data-contracts.md §6; ADR 0008).

`detect_deletions` diffs the durable STORED message set against a fresh LIVE
re-fetch over `range = [min..max]` of `stored ∪ live`:
- CONFIRMED / SNAPSHOT_DIFF = `stored − live` — captured, gone now (content kept).
- SUSPECTED / ID_GAP = `range − stored − live` — absent from both (no content).
The live set rescues every still-present id, so only genuinely-vanished slots
remain SUSPECTED. Pure + offline; `detected_at` is injected (deterministic tests).
"""

from datetime import datetime

from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.message import RawTelegramMessage


def _confirmed_evidence(
    message: RawTelegramMessage,
    channel_id: int,
    candidate_message_ids: set[int],
    detected_at: datetime,
) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        channel_id=channel_id,
        message_id=message.message_id,
        confidence=DeletionConfidence.CONFIRMED,
        method=DeletionMethod.SNAPSHOT_DIFF,
        original_text=message.text,
        first_seen_at=message.captured_at,
        detected_at=detected_at,
        was_signal_candidate=message.message_id in candidate_message_ids,
    )


def _suspected_evidence(
    message_id: int, channel_id: int, detected_at: datetime
) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        channel_id=channel_id,
        message_id=message_id,
        confidence=DeletionConfidence.SUSPECTED,
        method=DeletionMethod.ID_GAP,
        original_text=None,
        first_seen_at=None,
        detected_at=detected_at,
        was_signal_candidate=False,
    )


def _gap_ids(stored_ids: set[int], live_message_ids: set[int]) -> list[int]:
    universe = stored_ids | live_message_ids
    if not universe:
        return []
    # Floor the span at the oldest captured id: slots below it are pre-capture
    # (a depth-limited backfill starts partway in), never our deletions to claim.
    lower = min(stored_ids) if stored_ids else min(universe)
    span = range(lower, max(universe) + 1)
    return [
        mid for mid in span if mid not in stored_ids and mid not in live_message_ids
    ]


def detect_deletions(
    channel_id: int,
    stored: list[RawTelegramMessage],
    live_message_ids: set[int],
    candidate_message_ids: set[int],
    detected_at: datetime,
) -> list[DeletedSignalEvidence]:
    """Confirmed (stored − live) + suspected (range − stored − live) deletions."""
    stored_by_id = {message.message_id: message for message in stored}
    confirmed = [
        _confirmed_evidence(
            stored_by_id[mid], channel_id, candidate_message_ids, detected_at
        )
        for mid in sorted(set(stored_by_id) - live_message_ids)
    ]
    suspected = [
        _suspected_evidence(mid, channel_id, detected_at)
        for mid in _gap_ids(set(stored_by_id), live_message_ids)
    ]
    return confirmed + suspected
