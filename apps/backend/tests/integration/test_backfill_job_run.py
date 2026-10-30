from datetime import datetime, timezone
from uuid import uuid4

from fakes import FakeSource
from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import (
    backfill_job_repository,
    feed_repository,
    message_repository,
)
from verasig.features.feeds.backfill_job_coordinator import BackfillJobCoordinator
from verasig.features.feeds.backfill_job_run import BackfillMode, backfill_job_key
from verasig.features.feeds.history_depth import HistoryDepth, depth_cutoff
from verasig.foundation.jobs.registry import JobRegistry


def _instant() -> datetime:
    return datetime(2026, 6, 1, tzinfo=timezone.utc)


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


def _channel() -> TelegramChannel:
    return TelegramChannel(
        channel_id=7,
        handle="pilot",
        title="Pilot Signals",
        is_private=False,
        subscriber_count=1234,
        first_seen_at=_instant(),
    )


def _dated_message(message_id: int, posted_at: datetime) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=7,
        message_id=message_id,
        posted_at=posted_at,
        captured_at=posted_at,
        has_media=False,
        raw_payload={"id": message_id},
    )


def test_service_restart_marks_running_backfill_run_failed(session_factory):
    with session_factory() as session:
        account = account_repository.insert_account(session, _account())
        insert_source(session, account.id)
        feed_repository.create_feed(session, account.id, _channel(), _instant())
        feed_repository.set_status(session, account.id, 7, "backfilling")
        run = backfill_job_repository.create_run(session, account.id, 7, _instant())
        session.commit()

    coordinator = BackfillJobCoordinator(session_factory, JobRegistry(), batch_size=200)
    coordinator.mark_interrupted_runs_failed()

    with session_factory() as session:
        recovered = backfill_job_repository.read_run(session, run.id)
        feed = feed_repository.read_feed(session, account.id, 7)

    assert recovered.status == "failed"
    assert recovered.error_code == "SERVICE_INTERRUPTED"
    assert feed.status == "failed"


def test_service_restart_restores_reviewed_status_from_persisted_run(session_factory):
    # A backfill that started from a reviewed feed must restore that status on a
    # restart-driven recovery. The previous status is persisted on the run row, so
    # a FRESH coordinator (empty in-memory state, as after a restart) still reads it.
    with session_factory() as session:
        account = account_repository.insert_account(session, _account())
        insert_source(session, account.id)
        feed_repository.create_feed(session, account.id, _channel(), _instant())
        run = backfill_job_repository.create_run(
            session, account.id, 7, _instant(), previous_status="verified"
        )
        feed_repository.set_status(session, account.id, 7, "backfilling")
        session.commit()

    coordinator = BackfillJobCoordinator(session_factory, JobRegistry(), batch_size=200)
    coordinator.mark_interrupted_runs_failed()

    with session_factory() as session:
        recovered = backfill_job_repository.read_run(session, run.id)
        feed = feed_repository.read_feed(session, account.id, 7)

    assert recovered.status == "failed"  # the run itself still records the failure
    assert feed.status == "verified"  # but the reviewed feed status is restored


async def test_refresh_without_cursor_falls_back_to_depth_bounded_capture(
    session_factory, monkeypatch
):
    # A cursorless REFRESH has nothing to be "newer" than: an unbounded min_id=0
    # fetch would ignore the depth window and pull the whole channel. It must fall
    # back to a depth-bounded capture (extend_older, since == depth_cutoff) instead.
    fixed_now = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "verasig.features.feeds.backfill_job_coordinator._now", lambda: fixed_now
    )
    with session_factory() as session:
        account = account_repository.insert_account(session, _account())
        insert_source(session, account.id)
        feed_repository.create_feed(session, account.id, _channel(), _instant())
        # a prior capture SUCCEEDED but stored no messages (empty channel) → the top
        # cursor is still NULL even though the latest run status is "succeeded"
        run = backfill_job_repository.create_run(session, account.id, 7, _instant())
        backfill_job_repository.mark_run_succeeded(session, run.id, _instant())
        session.commit()
    user_id = account.id

    within_window = _dated_message(9, datetime(2026, 6, 1, tzinfo=timezone.utc))
    before_window = _dated_message(8, datetime(2025, 1, 1, tzinfo=timezone.utc))
    source = FakeSource(_channel(), [before_window, within_window])
    jobs = JobRegistry()
    coordinator = BackfillJobCoordinator(session_factory, jobs, batch_size=200)

    coordinator.start(user_id, 7, lambda: source, mode=BackfillMode.REFRESH)
    await jobs.channel(backfill_job_key(user_id, 7)).task

    assert source.requested_afters == []  # never did the unbounded newer fetch
    assert source.requested_befores == [None]  # paged older from the top instead
    assert source.requested_sinces == [depth_cutoff(HistoryDepth.ONE_YEAR, fixed_now)]
    with session_factory() as session:
        # only the within-window message was captured — the depth floor was honoured
        assert message_repository.count_messages(session, user_id, 7) == 1
