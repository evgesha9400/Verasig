"""Re-fetch full history = secure deletion evidence, then wipe & recapture (ADR 0014).

`secure_and_wipe` re-scans the live channel FIRST (so a CONFIRMED deletion's
original text is durably captured), then deletes the feed's capture + cascaded
derived rows in one transaction. Durable evidence, distilled rules and the
backfill-run history survive because they FK to `feed`, not to `raw_message`. An
inaccessible channel (empty live snapshot) aborts BEFORE anything is deleted.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fakes import FakeSource
from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel, LabelKind
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import ExtractedSignal, Side
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import (
    backfill_job_repository,
    deletion_repository,
    feed_repository,
    message_repository,
)
from verasig.features.feeds.deletion_rescan import RescanAborted
from verasig.features.feeds.recapture import secure_and_wipe
from verasig.features.rules import repository as rule_repository
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
        rule_repository.upsert_labels(
            session,
            [
                GoldenLabel(
                    user_id=account.id,
                    channel_id=1,
                    message_id=2,
                    label=LabelKind.SIGNAL,
                )
            ],
        )
        rule_repository.upsert_filter_rule(
            session,
            FilterRule(
                rule_id="r1",
                user_id=account.id,
                channel_id=1,
                include_patterns=["long"],
            ),
        )
        feed_repository.advance_cursor(session, account.id, 1, 3)
        backfill_job_repository.create_run(session, account.id, 1, _instant())
        session.commit()
        return account.id


async def test_secure_and_wipe_purges_capture_but_keeps_evidence_rules_runs(
    session_factory,
):
    user_id = _seed_feed_with_full_capture(session_factory)
    # message 2 vanished from the live channel — a CONFIRMED deletion to secure
    source = FakeSource(_channel(), [], live_ids={1, 3})

    result = await secure_and_wipe(source, user_id, 1, session_factory)

    with session_factory() as session:
        assert message_repository.count_messages(session, user_id, 1) == 0
        assert event_repository.read_signal_events(session, user_id, 1) == []
        assert outcome_repository.read_extracted_signals(session, 1, user_id) == []
        assert rule_repository.read_labels(session, 1, user_id) == []
        assert rule_repository.read_filter_rules(session, 1, user_id)  # rules survive
        assert backfill_job_repository.read_latest_run(session, user_id, 1) is not None
        assert feed_repository.read_cursor(session, user_id, 1) is None
        evidence = deletion_repository.read_deletion_evidence(session, user_id, 1)
    assert result.messages_deleted == 3
    secured = [item for item in evidence if item.message_id == 2]
    assert secured and secured[0].original_text == "BTC long 65k"


async def test_secure_and_wipe_aborts_before_wipe_on_empty_live_snapshot(
    session_factory,
):
    user_id = _seed_feed_with_full_capture(session_factory)
    source = FakeSource(_channel(), [], live_ids=set())  # inaccessible channel

    with pytest.raises(RescanAborted):
        await secure_and_wipe(source, user_id, 1, session_factory)

    with session_factory() as session:
        assert message_repository.count_messages(session, user_id, 1) == 3  # intact
        assert feed_repository.read_cursor(session, user_id, 1) == 3  # cursor intact
