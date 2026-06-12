from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.message import RawTelegramMessage
from verasig.services.projection.chats import present_chats
from verasig.services.projection.dates import format_long, format_short, format_time
from verasig.storage import (
    account_repository,
    backtest_repository,
    deletion_repository,
    user_channel_repository,
)
from verasig.storage import (
    repositories as repo,
)


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


def test_chat_summary_derives_counts_flags_score_and_display(db_session):
    account = account_repository.insert_account(db_session, _account())
    repo.upsert_channel(
        db_session,
        TelegramChannel(
            channel_id=7,
            handle="pilot",
            title="Pilot Signals",
            is_private=False,
            subscriber_count=1234,
            first_seen_at=_instant(),
        ),
    )
    repo.insert_messages(
        db_session,
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
    user_channel_repository.subscribe(db_session, account.id, 7, _instant())
    user_channel_repository.set_status(db_session, account.id, 7, "analyzed")
    deletion_repository.upsert_deletion_evidence(
        db_session,
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

    chat = present_chats(db_session, account.id)[0]

    assert chat["id"] == "7"
    assert chat["name"] == "Pilot Signals"
    assert chat["tag"] == "@pilot"
    assert chat["fetched"] == 2
    assert chat["lastDate"] == "Jun 7, 2025"
    assert chat["historyGaps"] is True
    assert chat["signalDeletion"] is True
    assert chat["score"] == 0
    assert chat["winRate"] == 61.5
    assert chat["pnl"] == 12.4
    assert chat["hasRisk"] is True
    assert chat["initials"] == "PS"
    assert chat["tint"].startswith("var(--viz-")
