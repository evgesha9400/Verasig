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


def _dated_message(message_id: int, posted_at: datetime) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=1,
        message_id=message_id,
        posted_at=posted_at,
        captured_at=posted_at,
        has_media=False,
        raw_payload={"id": message_id},
    )


def _account() -> UserAccount:
    return UserAccount(
        id=uuid4(),
        email="user@example.com",
        password_hash="hash",
        first_name="Ada",
        last_name="Lovelace",
        plan=Plan.FREE,
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


async def test_backfill_with_since_captures_only_messages_after_cutoff(session_factory):
    user_id = _seed_account(session_factory)
    old = _dated_message(1, datetime(2025, 1, 1, tzinfo=timezone.utc))
    recent = _dated_message(2, datetime(2026, 6, 1, tzinfo=timezone.utc))
    source = FakeSource(_channel(), [old, recent])
    since = datetime(2026, 1, 1, tzinfo=timezone.utc)

    result = await backfill(
        source, user_id, "@pilot", session_factory, batch_size=5, since=since
    )

    assert source.requested_sinces[0] == since
    assert result.inserted == 1
    with session_factory() as db_session:
        assert message_repository.count_messages(db_session, user_id, 1) == 1


async def test_refresh_fetches_newer_and_ignores_depth_cutoff(session_factory):
    user_id = _seed_account(session_factory)
    await backfill(
        FakeSource(_channel(), _messages(3)), user_id, "@pilot", session_factory, 5
    )
    # messages 4,5 arrived since; REFRESH pulls only what is newer than the top
    # cursor and ignores any depth cutoff (deepening is a full re-fetch, not this).
    resumed = FakeSource(_channel(), _messages(5))
    future_cutoff = datetime(2030, 1, 1, tzinfo=timezone.utc)

    result = await backfill(
        resumed,
        user_id,
        "@pilot",
        session_factory,
        batch_size=5,
        since=future_cutoff,
        extend_newer=True,
    )

    assert resumed.requested_afters[0] == 3  # fetch newer than the top cursor
    assert result.inserted == 2  # messages 4,5 captured, cutoff not applied


async def test_backfill_rerun_pages_below_oldest_and_adds_zero(session_factory):
    user_id = _seed_account(session_factory)
    await backfill(
        FakeSource(_channel(), _messages(5)), user_id, "@pilot", session_factory, 2
    )
    rerun = FakeSource(_channel(), _messages(5))
    result = await backfill(rerun, user_id, "@pilot", session_factory, batch_size=2)
    assert result.inserted == 0
    assert rerun.requested_befores[0] == 1  # paged strictly below the oldest captured
    with session_factory() as db_session:
        assert message_repository.count_messages(db_session, user_id, 1) == 5


async def test_backfill_resumes_older_from_oldest_captured_without_refetch(
    session_factory,
):
    user_id = _seed_account(session_factory)
    messages = _messages(6)
    crashed = FakeSource(_channel(), messages, fail_after_batch=1)
    with pytest.raises(FakeStreamInterrupted):
        await backfill(crashed, user_id, "@pilot", session_factory, batch_size=2)
    with session_factory() as db_session:
        # newest-first: the first batch captured ids 6,5 before the crash
        assert message_repository.count_messages(db_session, user_id, 1) == 2
        assert feed_repository.read_cursor(db_session, user_id, 1) == 6  # top cursor

    resumed = FakeSource(_channel(), messages)
    result = await backfill(resumed, user_id, "@pilot", session_factory, batch_size=2)
    assert resumed.requested_befores[0] == 5  # continue below the oldest captured id
    assert all(message_id < 5 for message_id in resumed.yielded_ids)
    assert result.captured_through_external_message_id == 6
    with session_factory() as db_session:
        assert message_repository.count_messages(db_session, user_id, 1) == 6


async def test_capture_insert_ignores_already_captured_ids(session_factory):
    user_id = _seed_account(session_factory)
    # first capture creates the feed and stores ids 1..3
    await backfill(
        FakeSource(_channel(), _messages(3)), user_id, "@pilot", session_factory, 5
    )
    # re-inserting captured ids is a no-op (ON CONFLICT DO NOTHING) — the invariant
    # newest-first resume relies on to never double-count a boundary message
    with session_factory() as db_session:
        reinserted = message_repository.insert_messages(
            db_session, user_id, _messages(3)
        )
        db_session.commit()
    assert reinserted == 0
    with session_factory() as db_session:
        assert message_repository.count_messages(db_session, user_id, 1) == 3


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
