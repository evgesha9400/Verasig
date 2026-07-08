"""Round-trip tests for the per-feed mine-result cache repository.

The cache holds the last mine's ``{groups, messages}`` snapshot so reopening a
verified feed hydrates the Verify audit without re-running the scan. A fresh mine
must replace (not accumulate) the snapshot, and deleting the feed must drop it.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import feed_repository
from verasig.features.mining.mine_result_repository import (
    read_mine_result,
    upsert_mine_result,
)

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
        plan=Plan.OBSERVER,
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


def test_read_mine_result_defaults_to_none(db_session):
    user_id = _seed_feed(db_session)
    assert read_mine_result(db_session, user_id, _EXTERNAL_ID) is None


def test_upsert_mine_result_round_trips_and_replaces(db_session):
    user_id = _seed_feed(db_session)

    first = {"groups": [{"templateKey": "tpl_a"}], "messages": [{"id": "1"}]}
    upsert_mine_result(db_session, user_id, _EXTERNAL_ID, first)
    db_session.commit()
    assert read_mine_result(db_session, user_id, _EXTERNAL_ID) == first

    second = {"groups": [{"templateKey": "tpl_b"}], "messages": []}
    upsert_mine_result(db_session, user_id, _EXTERNAL_ID, second)
    db_session.commit()
    assert read_mine_result(db_session, user_id, _EXTERNAL_ID) == second


def test_deleting_feed_cascades_the_mine_result(db_session):
    user_id = _seed_feed(db_session)
    upsert_mine_result(
        db_session, user_id, _EXTERNAL_ID, {"groups": [], "messages": []}
    )
    db_session.commit()

    feed_repository.delete_feed(db_session, user_id, _EXTERNAL_ID)
    db_session.commit()

    assert read_mine_result(db_session, user_id, _EXTERNAL_ID) is None
