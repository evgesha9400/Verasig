"""Persistence tests for immutable MiningReview revisions."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import feed_repository
from verasig.features.mining.mining_review import (
    create_review,
    read_input,
)
from verasig.features.mining.mining_review_repository import (
    read_latest_review_row,
    read_review_row,
)
from verasig.features.mining.template_mining import mine_template_groups

_EXTERNAL_ID = 7


def _instant() -> datetime:
    return datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def _account() -> UserAccount:
    return UserAccount(
        id=uuid4(),
        email="miner@example.com",
        password_hash="hash",
        first_name="Ada",
        last_name="Lovelace",
        plan=Plan.FREE,
        pending_email=None,
        cancel_at=None,
        created_at=_instant(),
    )


def _seed_feed(db_session) -> UUID:
    account = account_repository.insert_account(db_session, _account())
    insert_source(db_session, account.id)
    feed_repository.create_feed(
        db_session,
        account.id,
        TelegramChannel(
            channel_id=_EXTERNAL_ID,
            handle="pilot",
            title="Pilot Signals",
            is_private=False,
            first_seen_at=_instant(),
        ),
        _instant(),
    )
    return account.id


def _create_review(db_session, user_id):
    review_input = read_input(db_session, user_id, _EXTERNAL_ID)
    groups = mine_template_groups(review_input.messages, review_input.overlay)
    review = create_review(
        db_session,
        user_id,
        _EXTERNAL_ID,
        review_input,
        groups,
    )
    db_session.commit()
    return review


def test_read_review_defaults_to_none(db_session):
    user_id = _seed_feed(db_session)
    assert read_latest_review_row(db_session, user_id, _EXTERNAL_ID) is None


def test_create_review_appends_immutable_revisions(db_session):
    user_id = _seed_feed(db_session)

    first = _create_review(db_session, user_id)
    second = _create_review(db_session, user_id)

    assert first.review_id != second.review_id
    assert (
        read_review_row(
            db_session, user_id, _EXTERNAL_ID, first.review_id
        ).input_revision
        == first.input_revision
    )
    assert (
        read_latest_review_row(db_session, user_id, _EXTERNAL_ID).id == second.review_id
    )


def test_deleting_feed_cascades_mining_reviews(db_session):
    user_id = _seed_feed(db_session)
    review = _create_review(db_session, user_id)

    feed_repository.delete_feed(db_session, user_id, _EXTERNAL_ID)
    db_session.commit()

    assert read_review_row(db_session, user_id, _EXTERNAL_ID, review.review_id) is None
