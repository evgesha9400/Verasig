from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.message import RawTelegramMessage
from verasig.features.accounts import repository as account_repository
from verasig.features.simulation import repository as backtest_repository
from verasig.features.sources import (
    deletion_repository,
    feed_repository,
    message_repository,
)
from verasig.features.sources.feed_views import present_feeds
from verasig.shared.time import format_long, format_short, format_time


def _instant() -> datetime:
    return datetime(2025, 11, 18, 14, 32, tzinfo=timezone.utc)


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


def test_date_formatters():
    instant = _instant()

    assert format_long(instant) == "Nov 18, 2025"
    assert format_short(instant) == "Nov 18"
    assert format_time(instant) == "14:32"


def test_feed_summary_derives_counts_flags_score_and_display(db_session):
    account = account_repository.insert_account(db_session, _account())
    insert_source(db_session, account.id)
    feed_repository.create_feed(
        db_session,
        account.id,
        TelegramChannel(
            channel_id=7,
            handle="pilot",
            title="Pilot Signals",
            is_private=False,
            subscriber_count=1234,
            first_seen_at=_instant(),
        ),
        _instant(),
    )
    message_repository.insert_messages(
        db_session,
        account.id,
        [
            RawTelegramMessage(
                channel_id=7,
                message_id=1,
                text="BTC long",
                posted_at=_instant(),
                captured_at=_instant(),
                has_media=False,
                raw_payload={},
            ),
            RawTelegramMessage(
                channel_id=7,
                message_id=2,
                text="ETH long",
                posted_at=datetime(2025, 6, 7, 10, 0, tzinfo=timezone.utc),
                captured_at=_instant(),
                has_media=False,
                raw_payload={},
            ),
        ],
    )
    feed_repository.set_status(db_session, account.id, 7, "analyzed")
    deletion_repository.upsert_deletion_evidence(
        db_session,
        account.id,
        [
            DeletedSignalEvidence(
                channel_id=7,
                message_id=99,
                confidence=DeletionConfidence.SUSPECTED,
                method=DeletionMethod.ID_GAP,
                detected_at=_instant(),
                was_signal_candidate=False,
            )
        ],
    )
    deletion_repository.upsert_deletion_evidence(
        db_session,
        account.id,
        [
            DeletedSignalEvidence(
                channel_id=7,
                message_id=1,
                confidence=DeletionConfidence.CONFIRMED,
                method=DeletionMethod.SNAPSHOT_DIFF,
                detected_at=_instant(),
                was_signal_candidate=True,
            )
        ],
    )
    backtest_repository.insert_result(
        db_session,
        account.id,
        7,
        84,
        Decimal("61.5"),
        Decimal("12.4"),
        [],
        _instant(),
    )
    db_session.commit()

    feed = present_feeds(db_session, account.id)[0]

    assert feed["id"] == "7"
    assert feed["name"] == "Pilot Signals"
    assert feed["tag"] == "@pilot"
    assert feed["fetched"] == 2
    assert feed["lastDate"] == "Jun 7, 2025"
    assert feed["historyGaps"] is True
    assert feed["signalDeletion"] is True
    assert feed["score"] == 0
    assert feed["winRate"] == 61.5
    assert feed["pnl"] == 12.4
    assert feed["hasRisk"] is True
    assert feed["initials"] == "PS"
    assert feed["tint"].startswith("var(--viz-")
