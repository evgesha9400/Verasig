from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fakes import FakeSource, FakeStreamInterrupted
from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import (
    feed_repository,
    message_repository,
)
from verasig.features.feeds.backfill import backfill


def _instant() -> datetime:
    return datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)


def _channel() -> TelegramChannel:
    return TelegramChannel(
        channel_id=1,
        handle="pilot",
        title="Pilot",
        is_private=False,
        first_seen_at=_instant(),
    )


def _messages(count: int) -> list[RawTelegramMessage]:
    return [
        RawTelegramMessage(
            channel_id=1,
            message_id=i,
            posted_at=_instant(),
            captured_at=_instant(),
            has_media=False,
            raw_payload={"id": i},
        )
        for i in range(1, count + 1)
    ]


def _account() -> UserAccount:
    return UserAccount(
        id=uuid4(),
        email="user@example.com",
        password_hash="hash",
        first_name="Ada",
        last_name="Lovelace",
        plan=Plan.OBSERVER,
        pending_email=None,
        cancel_at=None,
        created_at=_instant(),
    )


def _seed_account(session_factory) -> UUID:
    with session_factory() as session:
        account = account_repository.insert_account(session, _account())
        insert_source(session, account.id)
        session.commit()
        return account.id


async def test_backfill_persists_all_messages(session_factory):
    user_id = _seed_account(session_factory)
    source = FakeSource(_channel(), _messages(5))
    result = await backfill(source, user_id, "@pilot", session_factory, batch_size=2)
    assert result.inserted == 5
    assert result.captured_through_external_message_id == 5
    with session_factory() as db_session:
        assert message_repository.count_messages(db_session, user_id, 1) == 5


async def test_backfill_idempotent_rerun_adds_zero_and_resumes(session_factory):
    user_id = _seed_account(session_factory)
    await backfill(
        FakeSource(_channel(), _messages(5)), user_id, "@pilot", session_factory, 2
    )
    rerun = FakeSource(_channel(), _messages(5))
    result = await backfill(rerun, user_id, "@pilot", session_factory, batch_size=2)
    assert result.inserted == 0
    assert rerun.requested_afters[0] == 5  # resumed at cursor, not 0
    with session_factory() as db_session:
        assert message_repository.count_messages(db_session, user_id, 1) == 5


async def test_backfill_resumes_from_cursor_without_refetch(session_factory):
    user_id = _seed_account(session_factory)
    messages = _messages(6)
    crashed = FakeSource(_channel(), messages, fail_after_batch=1)
    with pytest.raises(FakeStreamInterrupted):
        await backfill(crashed, user_id, "@pilot", session_factory, batch_size=2)
    with session_factory() as db_session:
        assert message_repository.count_messages(db_session, user_id, 1) == 2
        assert feed_repository.read_cursor(db_session, user_id, 1) == 2

    resumed = FakeSource(_channel(), messages)
    result = await backfill(resumed, user_id, "@pilot", session_factory, batch_size=2)
    assert resumed.requested_afters[0] == 2
    assert all(message_id > 2 for message_id in resumed.yielded_ids)
    assert result.captured_through_external_message_id == 6
    with session_factory() as db_session:
        assert message_repository.count_messages(db_session, user_id, 1) == 6


async def test_backfill_commits_each_batch_before_pulling_the_next(session_factory):
    user_id = _seed_account(session_factory)

    def assert_prior_batches_persisted(index: int, yielded_so_far: int) -> None:
        if index > 0:
            with session_factory() as db_session:
                assert (
                    message_repository.count_messages(db_session, user_id, 1)
                    == yielded_so_far
                )

    source = FakeSource(
        _channel(), _messages(2000), before_batch=assert_prior_batches_persisted
    )
    result = await backfill(source, user_id, "@pilot", session_factory, batch_size=200)
    assert result.inserted == 2000
    with session_factory() as db_session:
        assert message_repository.count_messages(db_session, user_id, 1) == 2000


async def test_backfill_reports_inserted_total_and_oldest_batch_date(session_factory):
    user_id = _seed_account(session_factory)
    seen: list[tuple[int, datetime]] = []

    source = FakeSource(_channel(), _messages(5))
    result = await backfill(
        source,
        user_id,
        "@pilot",
        session_factory,
        batch_size=2,
        on_batch=lambda inserted, oldest: seen.append((inserted, oldest)),
    )

    assert result.inserted == 5
    assert seen == [(2, _instant()), (4, _instant()), (5, _instant())]
