"""Atomic MiningReview confirmation.

Confirm locks the feed row, validates the addressed immutable review against the
live capture + overlay, replaces the signal projection, records review evidence,
and marks the feed verified in one transaction.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from verasig.domain.feed import FeedStatus
from verasig.domain.signal import Signal
from verasig.features.feeds import feed_repository
from verasig.features.mining import mining_review_repository
from verasig.features.mining.mining_audit import AuditResult, compute_audit
from verasig.features.mining.mining_review import require_current_review
from verasig.features.mining.mining_signals import candidate_to_signal
from verasig.features.mining.template_mining.types import TemplateGroup
from verasig.features.signals import outcome_repository

logger = logging.getLogger(__name__)


class MiningConfirmConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class MiningConfirmResult:
    feed_status: str
    templates_accepted: int
    signals_extracted: int


def confirm_review(
    session_factory: sessionmaker,
    user_id: UUID,
    external_id: int,
    review_id: UUID,
    accepted_template_keys: Sequence[str],
) -> MiningConfirmResult:
    accepted = set(accepted_template_keys)
    with session_factory() as session:
        feed = feed_repository.lock_feed(session, user_id, external_id)
        if feed is None:
            raise MiningConfirmConflictError(f"feed {external_id} no longer exists")
        if feed.status == FeedStatus.BACKFILLING:
            raise MiningConfirmConflictError(
                "A backfill is running for this feed; confirm again once it finishes."
            )

        review = require_current_review(session, user_id, external_id, review_id)
        kept = [group for group in review.groups if group.template_key in accepted]
        signals = _signals_of(kept, external_id)
        audit = compute_audit(
            review.messages,
            review.groups,
            accepted_template_keys,
            review.overlay,
        )

        outcome_repository.delete_signals_for_channel(session, user_id, external_id)
        extracted = outcome_repository.insert_signals(session, signals, user_id)
        feed.status = FeedStatus.VERIFIED
        review_row = mining_review_repository.read_review_row(
            session, user_id, external_id, review_id
        )
        mining_review_repository.mark_review_confirmed(
            review_row,
            [group.template_key for group in kept],
            _missed_message_ids(audit, signals),
            datetime.now(tz=UTC),
        )
        session.commit()

    logger.info(
        "mining.confirm done: external_id=%s review_id=%s templates=%s "
        "signals=%s status=%s",
        external_id,
        review_id,
        len(kept),
        extracted,
        FeedStatus.VERIFIED,
    )
    return MiningConfirmResult(
        feed_status=FeedStatus.VERIFIED,
        templates_accepted=len(kept),
        signals_extracted=extracted,
    )


def read_confirmed_template_keys(
    session_factory: sessionmaker, user_id: UUID, external_id: int
) -> list[str]:
    with session_factory() as session:
        return outcome_repository.read_confirmed_template_keys(
            session, user_id, external_id
        )


def _signals_of(groups: Sequence[TemplateGroup], external_id: int) -> list[Signal]:
    return [
        signal
        for group in groups
        for candidate in group.candidates
        if (signal := candidate_to_signal(candidate, external_id)) is not None
    ]


def _missed_message_ids(audit: AuditResult, signals: Sequence[Signal]) -> list[int]:
    candidate_ids = {
        int(candidate.message.id) for candidate in audit.ambiguous_candidates
    }
    candidate_ids.update(
        int(candidate.message.id)
        for group in audit.rare_templates
        for candidate in group.candidates
    )
    candidate_ids.update(int(message.id) for message in audit.potential_misses)
    extracted_ids = {signal.message_id for signal in signals}
    return sorted(candidate_ids - extracted_ids)
