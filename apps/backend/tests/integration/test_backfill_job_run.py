from datetime import datetime, timezone
from uuid import uuid4

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.features.accounts import repository as account_repository
from verasig.features.sources import backfill_job_repository, feed_repository
from verasig.features.sources.backfill_job_coordinator import BackfillJobCoordinator
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
        plan=Plan.OBSERVER,
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
