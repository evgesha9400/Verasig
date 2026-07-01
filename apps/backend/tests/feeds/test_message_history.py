from datetime import datetime, timezone
from uuid import uuid4

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.label import LabelKind
from verasig.domain.message import RawTelegramMessage
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import feed_repository, message_repository
from verasig.features.feeds.message_views import read_history
from verasig.features.rules.labeling import record_label
from verasig.features.signals import event_repository


def _instant(day: int = 1) -> datetime:
    return datetime(2026, 6, day, 14, 32, tzinfo=timezone.utc)


def _account() -> UserAccount:
    return UserAccount(
        id=uuid4(),
        email="historian@example.com",
        password_hash="hash",
        first_name="Ada",
        last_name="Lovelace",
        plan=Plan.OBSERVER,
        pending_email=None,
        cancel_at=None,
        created_at=_instant(),
    )


def _seed(db_session):
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
                posted_at=_instant(1),
                captured_at=_instant(1),
                has_media=False,
                raw_payload={},
            ),
            RawTelegramMessage(
                channel_id=7,
                message_id=2,
                text="reply target",
                posted_at=_instant(2),
                captured_at=_instant(2),
                has_media=False,
                raw_payload={},
            ),
            RawTelegramMessage(
                channel_id=7,
                message_id=3,
                text="ETH long",
                posted_at=_instant(3),
                captured_at=_instant(3),
                reply_to_message_id=2,
                has_media=True,
                raw_payload={"photo": {"id": 1}},
            ),
        ],
    )
    # Only message 1 and 3 are signal candidates; message 2 is not.
    event_repository.insert_signal_events(
        db_session,
        account.id,
        [
            RawSignalEvent(
                channel_id=7,
                message_id=1,
                candidate_text="BTC long",
                materialized_by=MaterializationPath.SEED_HEURISTIC,
            ),
            RawSignalEvent(
                channel_id=7,
                message_id=3,
                candidate_text="ETH long",
                materialized_by=MaterializationPath.SEED_HEURISTIC,
            ),
        ],
    )
    db_session.commit()
    return account


def test_read_history_returns_every_message_regardless_of_label_or_candidacy(
    db_session,
):
    account = _seed(db_session)
    # Labeling a message must NOT drop it from the full history (unlike the
    # labeling sample, which excludes labeled + non-candidate messages).
    record_label(db_session, account.id, 7, 1, LabelKind.NOISE)
    db_session.commit()

    channel = feed_repository.read_feed(db_session, account.id, 7)
    history = read_history(db_session, channel)

    # Every stored message is present, oldest first — including the labeled one
    # (1) and the non-candidate one (2), which the labeling sample would omit.
    assert [message["id"] for message in history] == ["1", "2", "3"]
    assert history[0]["author"] == "Pilot Signals"
    assert history[2]["media"] == "image"
    assert history[2]["replyTo"] == {"author": "Pilot Signals", "text": "reply target"}
