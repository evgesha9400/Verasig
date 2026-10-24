"""Revisioned MiningReview domain seam.

A review freezes the exact ordered message corpus, mined families, and parser
overlay shown to the operator. Audit and Confirm address that snapshot by UUID
and reject it once the live capture generation, message content, or overlay no
longer matches its input revision.
"""

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from verasig.features.feeds import feed_repository, message_repository
from verasig.features.mining import mining_review_repository
from verasig.features.mining.template_mining.mining import MINER_VERSION
from verasig.features.mining.template_mining.types import ChatMessage, TemplateGroup
from verasig.features.parser_overlay.repository import read_overlay


class MiningReviewNotFoundError(LookupError):
    pass


class MiningReviewStaleError(RuntimeError):
    pass


@dataclass(frozen=True)
class MiningReviewInput:
    messages: list[ChatMessage]
    overlay: dict
    capture_generation: int
    input_revision: str


@dataclass(frozen=True)
class MiningReview:
    review_id: UUID
    user_id: UUID
    external_id: int
    input_revision: str
    groups: list[TemplateGroup]
    messages: list[ChatMessage]
    overlay: dict
    created_at: datetime

    @property
    def payload(self) -> dict:
        return {
            "groups": [asdict(group) for group in self.groups],
            "messages": [asdict(message) for message in self.messages],
        }


def _to_chat_message(message) -> ChatMessage:
    return ChatMessage(
        id=str(message.message_id),
        text=message.text or "",
        date=message.posted_at.isoformat() if message.posted_at else None,
    )


def _digest(value: object) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(serialized.encode()).hexdigest()


def input_revision(
    messages: Sequence[ChatMessage], overlay: dict, capture_generation: int
) -> str:
    return _digest(
        {
            "captureGeneration": capture_generation,
            "minerVersion": MINER_VERSION,
            "messages": [
                {"id": message.id, "text": message.text, "date": message.date}
                for message in messages
            ],
            "overlay": overlay,
        }
    )


def read_input(session: Session, user_id: UUID, external_id: int) -> MiningReviewInput:
    feed = feed_repository.read_feed(session, user_id, external_id)
    if feed is None:
        raise MiningReviewNotFoundError(f"feed {external_id} not found")
    raw_messages = message_repository.read_messages(session, user_id, external_id)
    messages = [_to_chat_message(message) for message in raw_messages]
    overlay = read_overlay(session, user_id)
    return MiningReviewInput(
        messages=messages,
        overlay=overlay,
        capture_generation=feed.capture_generation,
        input_revision=input_revision(messages, overlay, feed.capture_generation),
    )


def create_review(
    session: Session,
    user_id: UUID,
    external_id: int,
    review_input: MiningReviewInput,
    groups: list[TemplateGroup],
) -> MiningReview:
    review = MiningReview(
        review_id=uuid4(),
        user_id=user_id,
        external_id=external_id,
        input_revision=review_input.input_revision,
        groups=groups,
        messages=review_input.messages,
        overlay=review_input.overlay,
        created_at=datetime.now(tz=UTC),
    )
    mining_review_repository.insert_review(session, review)
    return review


def _from_row(row) -> MiningReview:
    return MiningReview(
        review_id=row.id,
        user_id=row.user_id,
        external_id=row.external_id,
        input_revision=row.input_revision,
        groups=mining_review_repository.decode_groups(row),
        messages=mining_review_repository.decode_messages(row),
        overlay=dict(row.overlay),
        created_at=row.created_at,
    )


def require_current_review(
    session: Session, user_id: UUID, external_id: int, review_id: UUID
) -> MiningReview:
    row = mining_review_repository.read_review_row(
        session, user_id, external_id, review_id
    )
    if row is None:
        raise MiningReviewNotFoundError(f"mining review {review_id} not found")
    _require_revision(session, user_id, external_id, row.input_revision)
    return _from_row(row)


def require_latest_current_review(
    session: Session, user_id: UUID, external_id: int
) -> MiningReview:
    row = mining_review_repository.read_latest_review_row(session, user_id, external_id)
    if row is None:
        raise MiningReviewNotFoundError("no mining review exists")
    _require_revision(session, user_id, external_id, row.input_revision)
    return _from_row(row)


def read_confirmed_missed_message_ids(
    session: Session, user_id: UUID, external_id: int
) -> list[int]:
    """The misses of the latest confirmed review. The same confirm wrote them and
    the stored signal set, so they stay paired even after new messages make the
    review stale; dropping them would score parser confidence as a perfect 1.0."""
    row = mining_review_repository.read_latest_confirmed_review_row(
        session, user_id, external_id
    )
    if row is None:
        return []
    return [int(message_id) for message_id in row.missed_message_ids or []]


def _require_revision(
    session: Session,
    user_id: UUID,
    external_id: int,
    expected_revision: str,
) -> None:
    current_revision = read_input(session, user_id, external_id).input_revision
    if current_revision != expected_revision:
        raise MiningReviewStaleError(
            "The feed messages or parser overlay changed after this review was mined."
        )
