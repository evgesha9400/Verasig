"""Re-fetch full history = verify reachability, then wipe & recapture (ADR 0014).

`guard_and_wipe` verifies the channel still resolves FIRST, then deletes the
feed's capture + cascaded derived rows in one transaction. It secures NO deletion
evidence (that is the deliberate `Check gaps` rescan). Durable evidence and the
backfill-run history survive because they FK to `feed`, not to `raw_message`. An
unreachable channel aborts BEFORE anything is deleted.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fakes import FakeSource
from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import ExtractedSignal, Side
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import (
    backfill_job_repository,
    deletion_repository,
    feed_repository,
    message_repository,
)
from verasig.features.feeds.recapture import ChannelUnreachableError, guard_and_wipe
from verasig.features.signals import event_repository, outcome_repository


def _instant() -> datetime:
    return datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)


def _channel() -> TelegramChannel:
    return TelegramChannel(
        channel_id=1, title="Pilot", is_private=False, first_seen_at=_instant()
    )


def _message(message_id: int, text: str = "msg") -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=1,
        message_id=message_id,
        text=text,
        posted_at=_instant(),
        captured_at=_instant(),
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
        plan=Plan.OBSERVER,
        pending_email=None,
        cancel_at=None,
        created_at=_instant(),
    )


def _seed_feed_with_full_capture(session_factory) -> object:
    with session_factory() as session:
        account = account_repository.insert_account(session, _account())
        insert_source(session, account.id)
        feed_repository.create_feed(session, account.id, _channel(), _instant())
        message_repository.insert_messages(
            session,
            account.id,
            [_message(1), _message(2, "BTC long 65k"), _message(3)],
        )
        event = RawSignalEvent(
            channel_id=1,
            message_id=2,
            candidate_text="BTC long 65k",
            materialized_by=MaterializationPath.SEED_HEURISTIC,
            created_at=_instant(),
        )
        event_repository.insert_signal_events(session, account.id, [event])
        outcome_repository.insert_extracted_signals(
            session,
            [
                ExtractedSignal(
                    event_id=event.id, channel_id=1, symbol="BTC", side=Side.LONG
                )
            ],
            account.id,
        )
        feed_repository.advance_cursor(session, account.id, 1, 3)
        backfill_job_repository.create_run(session, account.id, 1, _instant())
        session.commit()
        return account.id


async def test_guard_and_wipe_purges_capture_but_keeps_evidence_and_runs(
    session_factory,
):
    user_id = _seed_feed_with_full_capture(session_factory)
    source = FakeSource(_channel(), [])

    deleted = await guard_and_wipe(source, user_id, 1, session_factory)

    with session_factory() as session:
        assert message_repository.count_messages(session, user_id, 1) == 0
        assert event_repository.read_signal_events(session, user_id, 1) == []
        assert outcome_repository.read_extracted_signals(session, 1, user_id) == []
        assert backfill_job_repository.read_latest_run(session, user_id, 1) is not None
        assert feed_repository.read_cursor(session, user_id, 1) is None
        # a clean wipe secures NO deletion evidence (that is the Check gaps rescan)
        assert deletion_repository.read_deletion_evidence(session, user_id, 1) == []
    assert deleted == 3


async def test_guard_and_wipe_aborts_before_wipe_when_channel_unreachable(
    session_factory,
):
    user_id = _seed_feed_with_full_capture(session_factory)
    # channel no longer resolves — never wipe a capture we cannot refill
    source = FakeSource(_channel(), [], resolve_error=RuntimeError("channel gone"))

    with pytest.raises(ChannelUnreachableError):
        await guard_and_wipe(source, user_id, 1, session_factory)

    with session_factory() as session:
        assert message_repository.count_messages(session, user_id, 1) == 3  # intact
        assert feed_repository.read_cursor(session, user_id, 1) == 3  # cursor intact
