"""Deletion repository functions.

The domain `DeletedSignalEvidence` speaks `channel_id`/`message_id`; storage
speaks `external_id`/`external_message_id` and is user-owned.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.deletion import DeletedSignalEvidence
from verasig.storage.models import DeletedSignalEvidenceRow


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
