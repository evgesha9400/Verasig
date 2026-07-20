"""Persistence for immutable, revisioned MiningReview snapshots."""

from datetime import datetime
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from verasig.features.mining.template_mining.types import ChatMessage, TemplateGroup
from verasig.storage.models import MiningReviewRow

_MESSAGES = TypeAdapter(list[ChatMessage])
_GROUPS = TypeAdapter(list[TemplateGroup])


def insert_review(session: Session, review) -> None:
    session.add(
        MiningReviewRow(
            id=review.review_id,
            user_id=review.user_id,
            external_id=review.external_id,
            input_revision=review.input_revision,
            payload=review.payload,
            overlay=review.overlay,
            created_at=review.created_at,
        )
    )
    session.flush()


def read_review_row(
    session: Session, user_id: UUID, external_id: int, review_id: UUID
) -> MiningReviewRow | None:
    return session.scalar(
        select(MiningReviewRow).where(
            MiningReviewRow.id == review_id,
            MiningReviewRow.user_id == user_id,
            MiningReviewRow.external_id == external_id,
        )
    )


def read_latest_review_row(
    session: Session, user_id: UUID, external_id: int
) -> MiningReviewRow | None:
    return session.scalar(
        select(MiningReviewRow)
        .where(
            MiningReviewRow.user_id == user_id,
            MiningReviewRow.external_id == external_id,
        )
        .order_by(MiningReviewRow.created_at.desc(), MiningReviewRow.id.desc())
        .limit(1)
    )


def read_latest_confirmed_review_row(
    session: Session, user_id: UUID, external_id: int
) -> MiningReviewRow | None:
    return session.scalar(
        select(MiningReviewRow)
        .where(
            MiningReviewRow.user_id == user_id,
            MiningReviewRow.external_id == external_id,
            MiningReviewRow.confirmed_at.is_not(None),
        )
        .order_by(MiningReviewRow.confirmed_at.desc(), MiningReviewRow.id.desc())
        .limit(1)
    )


def mark_review_confirmed(
    row: MiningReviewRow,
    accepted_template_keys: list[str],
    missed_message_ids: list[int],
    confirmed_at: datetime,
) -> None:
    row.accepted_template_keys = accepted_template_keys
    row.missed_message_ids = missed_message_ids
    row.confirmed_at = confirmed_at


def decode_messages(row: MiningReviewRow) -> list[ChatMessage]:
    return _MESSAGES.validate_python(row.payload["messages"])


def decode_groups(row: MiningReviewRow) -> list[TemplateGroup]:
    return _GROUPS.validate_python(row.payload["groups"])
