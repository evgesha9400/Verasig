from datetime import datetime, timezone
from uuid import uuid4

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.label import LabelKind
from verasig.domain.message import RawTelegramMessage
from verasig.features.accounts import repository as account_repository
from verasig.features.rules.labeling import (
    label_counts,
    labeling_sample,
    record_label,
)
from verasig.features.signals import event_repository
from verasig.features.sources import (
    channel_repository,
    message_repository,
)
from verasig.features.sources import subscription_repository as user_channel_repository


def _instant(day: int = 1) -> datetime:
    return datetime(2026, 6, day, 14, 32, tzinfo=timezone.utc)


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


def _seed(db_session):
    account = account_repository.insert_account(db_session, _account())
    channel_repository.upsert_channel(
        db_session,
        TelegramChannel(
            channel_id=7,
            handle="pilot",
            title="Pilot Signals",
            is_private=False,
            first_seen_at=_instant(),
        ),
    )
    message_repository.insert_messages(
        db_session,
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
    event_repository.insert_signal_events(
        db_session,
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
    user_channel_repository.subscribe(db_session, account.id, 7, _instant())
    db_session.commit()
    return account


def test_labeling_sample_returns_unlabeled_candidate_messages_oldest_first(db_session):
    account = _seed(db_session)
    record_label(db_session, account.id, 7, 1, LabelKind.NOISE)
    db_session.commit()

    messages = labeling_sample(db_session, account.id, 7, limit=40)

    assert [message["id"] for message in messages] == ["3"]
    assert messages[0]["author"] == "Pilot Signals"
    assert messages[0]["media"] == "image"
    assert messages[0]["replyTo"] == {"author": "Pilot Signals", "text": "reply target"}


def test_record_label_upserts_and_counts_by_kind(db_session):
    account = _seed(db_session)

    record_label(db_session, account.id, 7, 1, LabelKind.SIGNAL)
    record_label(db_session, account.id, 7, 1, LabelKind.MODIFIER)
    record_label(db_session, account.id, 7, 3, LabelKind.NOISE)
    db_session.commit()

    assert label_counts(db_session, account.id, 7) == {
        "signalCount": 0,
        "noiseCount": 1,
        "modifierCount": 1,
        "total": 2,
    }
