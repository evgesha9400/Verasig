"""Deletion repository functions.

The domain `DeletedSignalEvidence` speaks `channel_id`/`message_id`; storage
speaks `external_id`/`external_message_id` and is user-owned.
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.deletion import DeletedSignalEvidence
from verasig.storage.models import DeletedSignalEvidenceRow, GoldenLabelRow


@dataclass(frozen=True)
class DeletionSummary:
    # Confirmed deletions only. Suspected id-gaps are detected and persisted for
    # provider-hygiene scoring, but never surfaced to the user (no value).
    signal_deletion: bool = False
    deleted_count: int = 0
    deleted_signal_count: int = 0


def _deletion_values(user_id: UUID, evidence: DeletedSignalEvidence) -> dict:
    return {
        "id": evidence.id,
        "user_id": user_id,
        "external_id": evidence.channel_id,
        "external_message_id": evidence.message_id,
        "confidence": evidence.confidence.value,
        "method": evidence.method.value,
        "original_text": evidence.original_text,
        "first_seen_at": evidence.first_seen_at,
        "detected_at": evidence.detected_at,
        "was_signal_candidate": evidence.was_signal_candidate,
    }


def upsert_deletion_evidence(
    session: Session, user_id: UUID, evidence: list[DeletedSignalEvidence]
) -> int:
    """Persist evidence; upgrade SUSPECTED->CONFIRMED only, preserving detected_at."""
    if not evidence:
        return 0
    statement = pg_insert(DeletedSignalEvidenceRow).values(
        [_deletion_values(user_id, item) for item in evidence]
    )
    statement = statement.on_conflict_do_update(
        index_elements=["user_id", "external_id", "external_message_id"],
        set_={
            "confidence": statement.excluded.confidence,
            "method": statement.excluded.method,
            "original_text": statement.excluded.original_text,
            "first_seen_at": statement.excluded.first_seen_at,
            "was_signal_candidate": statement.excluded.was_signal_candidate,
        },
        where=(
            (DeletedSignalEvidenceRow.confidence == "SUSPECTED")
            & (statement.excluded.confidence == "CONFIRMED")
        ),
    ).returning(DeletedSignalEvidenceRow.id)
    return len(session.execute(statement).fetchall())


def _row_to_deletion(row: DeletedSignalEvidenceRow) -> DeletedSignalEvidence:
    return DeletedSignalEvidence(
        id=row.id,
        channel_id=row.external_id,
        message_id=row.external_message_id,
        confidence=row.confidence,
        method=row.method,
        original_text=row.original_text,
        first_seen_at=row.first_seen_at,
        detected_at=row.detected_at,
        was_signal_candidate=row.was_signal_candidate,
    )


def update_evidence_candidacy(
    session: Session,
    user_id: UUID,
    external_id: int,
    decide: Callable[[int, str | None], bool],
) -> int:
    """Recompute `was_signal_candidate` for CONFIRMED evidence from `decide`.

    `decide(message_id, original_text)` is rule-authoritative (ADR 0015). Only
    CONFIRMED rows carry text; post-wipe they have no surviving `raw_message`, so
    `decide` must fall back to the retained `original_text`. Returns rows changed.
    """
    rows = session.scalars(
        select(DeletedSignalEvidenceRow).where(
            DeletedSignalEvidenceRow.user_id == user_id,
            DeletedSignalEvidenceRow.external_id == external_id,
            DeletedSignalEvidenceRow.confidence == "CONFIRMED",
        )
    ).all()
    changed = 0
    for row in rows:
        decided = decide(row.external_message_id, row.original_text)
        if row.was_signal_candidate != decided:
            row.was_signal_candidate = decided
            changed += 1
    session.flush()
    return changed


def read_deletion_evidence(
    session: Session, user_id: UUID, external_id: int
) -> list[DeletedSignalEvidence]:
    rows = session.scalars(
        select(DeletedSignalEvidenceRow).where(
            DeletedSignalEvidenceRow.user_id == user_id,
            DeletedSignalEvidenceRow.external_id == external_id,
        )
    ).all()
    return [_row_to_deletion(row) for row in rows]


def _is_signal_deletion(
    confidence: str,
    was_candidate: bool,
    label: str | None,
    external_id: int,
    rule_backed_ids: frozenset[int],
) -> bool:
    """A CONFIRMED deletion counts as a signal via a golden label (legacy) or,
    once the feed has saved rules, its rule-authoritative candidacy (ADR 0015).
    The rule gate stops recall-first seed candidacy flooring the score before the
    operator has approved any rules."""
    if confidence != "CONFIRMED":
        return False
    if label == "signal":
        return True
    return bool(was_candidate) and external_id in rule_backed_ids


def summarize_deletions(
    session: Session,
    user_id: UUID,
    external_ids: list[int],
    rule_backed_ids: frozenset[int] = frozenset(),
) -> dict[int, DeletionSummary]:
    if not external_ids:
        return {}
    rows = session.execute(
        select(
            DeletedSignalEvidenceRow.external_id,
            DeletedSignalEvidenceRow.confidence,
            DeletedSignalEvidenceRow.was_signal_candidate,
            GoldenLabelRow.label,
        )
        .outerjoin(
            GoldenLabelRow,
            (GoldenLabelRow.user_id == DeletedSignalEvidenceRow.user_id)
            & (GoldenLabelRow.external_id == DeletedSignalEvidenceRow.external_id)
            & (
                GoldenLabelRow.external_message_id
                == DeletedSignalEvidenceRow.external_message_id
            ),
        )
        .where(
            DeletedSignalEvidenceRow.user_id == user_id,
            DeletedSignalEvidenceRow.external_id.in_(external_ids),
        )
    ).all()
    summaries = {external_id: DeletionSummary() for external_id in external_ids}
    for external_id, confidence, was_candidate, label in rows:
        if confidence != "CONFIRMED":
            continue  # suspected id-gaps are internal-only (hygiene), never surfaced
        current = summaries[external_id]
        is_signal = _is_signal_deletion(
            confidence, was_candidate, label, external_id, frozenset(rule_backed_ids)
        )
        summaries[external_id] = DeletionSummary(
            signal_deletion=current.signal_deletion or is_signal,
            deleted_count=current.deleted_count + 1,
            deleted_signal_count=current.deleted_signal_count + int(is_signal),
        )
    return summaries
