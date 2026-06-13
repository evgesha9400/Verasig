from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.label import GoldenLabel, LabelKind
from verasig.domain.message import RawTelegramMessage
from verasig.domain.risk_config import EntryMode, RiskConfig
from verasig.features.accounts import repository as account_repository
from verasig.features.exchanges import repository as exchange_repository
from verasig.features.risk import repository as risk_repository
from verasig.features.rules import repository as rule_repository
from verasig.features.signals import (
    lifecycle_link_repository,
)
from verasig.features.simulation import repository as backtest_repository
from verasig.features.sources import (
    channel_repository,
    message_repository,
)
from verasig.features.sources import subscription_repository as user_channel_repository
from verasig.features.telegram_links import repository as telegram_link_repository
from verasig.storage.models import ChannelRow


def _instant() -> datetime:
    return datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)


def _channel(**overrides) -> TelegramChannel:
    base = {
        "channel_id": 1,
        "title": "Pilot",
        "is_private": False,
        "first_seen_at": _instant(),
    }
    base.update(overrides)
    return TelegramChannel(**base)


def _message(message_id: int, channel_id: int = 1) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=channel_id,
        message_id=message_id,
        posted_at=_instant(),
        captured_at=_instant(),
        has_media=False,
        raw_payload={"id": message_id},
    )


def _account(email: str = "user@example.com") -> UserAccount:
    return UserAccount(
        id=uuid4(),
        email=email,
        password_hash="hash",
        first_name="Ada",
        last_name="Lovelace",
        plan=Plan.OBSERVER,
        pending_email=None,
        cancel_at=None,
        created_at=_instant(),
    )


def test_insert_messages_dedups_on_conflict(db_session):
    channel_repository.upsert_channel(db_session, _channel())
    db_session.commit()
    inserted_first = message_repository.insert_messages(
        db_session, [_message(1), _message(2)]
    )
    db_session.commit()
    inserted_again = message_repository.insert_messages(
        db_session, [_message(2), _message(3)]
    )
    db_session.commit()
    assert inserted_first == 2
    assert inserted_again == 1
    assert message_repository.count_messages(db_session, 1) == 3


def test_advance_cursor_is_monotonic(db_session):
    channel_repository.upsert_channel(db_session, _channel())
    db_session.commit()
    channel_repository.advance_cursor(db_session, 1, 50)
    db_session.commit()
    channel_repository.advance_cursor(db_session, 1, 30)
    db_session.commit()
    assert channel_repository.read_cursor(db_session, 1) == 50


def test_read_cursor_is_none_for_unknown_channel(db_session):
    assert channel_repository.read_cursor(db_session, 999) is None


def test_upsert_channel_updates_metadata_but_preserves_first_seen_and_cursor(
    db_session,
):
    channel_repository.upsert_channel(db_session, _channel(subscriber_count=100))
    db_session.commit()
    channel_repository.advance_cursor(db_session, 1, 42)
    db_session.commit()

    later = datetime(2027, 1, 1, tzinfo=timezone.utc)
    channel_repository.upsert_channel(
        db_session,
        _channel(title="Renamed", subscriber_count=200, first_seen_at=later),
    )
    db_session.commit()

    channel = db_session.get(ChannelRow, 1)
    assert channel.title == "Renamed"
    assert channel.subscriber_count == 200
    assert channel.first_seen_at == _instant()
    assert channel_repository.read_cursor(db_session, 1) == 42


def test_account_repository_round_trips_profile_plan_and_email(db_session):
    account = account_repository.insert_account(db_session, _account())
    db_session.commit()

    assert account_repository.find_by_email(db_session, "user@example.com") == account
    renamed = account_repository.update_profile(
        db_session, account.id, "Grace", "Hopper"
    )
    pending = account_repository.set_pending_email(
        db_session, account.id, "next@example.com"
    )
    applied = account_repository.apply_pending_email(db_session, account.id)
    planned = account_repository.set_plan(db_session, account.id, Plan.DESK)
    cancelled = account_repository.set_cancel_at(db_session, account.id, _instant())

    assert renamed.first_name == "Grace"
    assert pending.pending_email == "next@example.com"
    assert applied.email == "next@example.com"
    assert planned.plan is Plan.DESK
    assert cancelled.cancel_at == _instant()


def test_telegram_link_repository_round_trips_pending_and_connected(db_session):
    account = account_repository.insert_account(db_session, _account())
    db_session.commit()

    pending = telegram_link_repository.upsert_pending(
        db_session,
        account.id,
        123,
        "api-hash-envelope",
        "+15551234567",
        "phone-code-hash",
        _instant(),
    )
    assert pending.status == "pending"

    connected = telegram_link_repository.mark_connected(
        db_session, account.id, "session-envelope", _instant()
    )

    assert connected.status == "connected"
    assert (
        telegram_link_repository.read_link(db_session, account.id).phone
        == "+15551234567"
    )


def test_user_channel_repository_round_trips_and_cascades_user_scope(db_session):
    account = account_repository.insert_account(db_session, _account())
    channel_repository.upsert_channel(db_session, _channel())
    db_session.commit()

    subscription = user_channel_repository.subscribe(
        db_session, account.id, 1, _instant()
    )
    rule_repository.upsert_labels(
        db_session,
        [
            GoldenLabel(
                user_id=account.id,
                channel_id=1,
                message_id=99,
                label=LabelKind.SIGNAL,
            )
        ],
    )
    db_session.commit()

    assert subscription.status == "new"
    assert user_channel_repository.count_subscriptions(db_session, account.id) == 1
    assert user_channel_repository.bump_verify_attempt(db_session, account.id, 1) == 2
    assert (
        user_channel_repository.set_status(db_session, account.id, 1, "verified").status
        == "verified"
    )

    user_channel_repository.unsubscribe(db_session, account.id, 1)
    db_session.commit()

    assert user_channel_repository.read_subscription(db_session, account.id, 1) is None
    assert rule_repository.read_labels(db_session, 1, account.id) == []


def test_exchange_risk_backtest_and_lifecycle_repositories_round_trip(db_session):
    account = account_repository.insert_account(db_session, _account())
    channel_repository.upsert_channel(db_session, _channel())
    db_session.commit()

    exchange = exchange_repository.upsert_connection(
        db_session,
        account.id,
        "bybit",
        "J7n2...wL",
        "key-envelope",
        "secret-envelope",
        True,
        _instant(),
    )
    exchange_repository.set_connected(db_session, account.id, "bybit", False)
    config = risk_repository.upsert_risk_config(
        db_session,
        account.id,
        1,
        RiskConfig(entry_mode=EntryMode.FIRST),
        _instant(),
    )
    first_result = backtest_repository.insert_result(
        db_session,
        account.id,
        1,
        80,
        Decimal("55.5"),
        Decimal("12.3"),
        [{"rootSignalId": "a"}],
        _instant(),
    )
    second_result = backtest_repository.insert_result(
        db_session,
        account.id,
        1,
        90,
        Decimal("66.6"),
        Decimal("22.3"),
        [{"rootSignalId": "b"}],
        datetime(2026, 6, 4, 13, 0, tzinfo=timezone.utc),
    )
    link = lifecycle_link_repository.insert_link(
        db_session, account.id, 1, 77, uuid4(), _instant()
    )
    db_session.commit()

    assert exchange.exchange_id == "bybit"
    assert (
        exchange_repository.read_connections(db_session, account.id)[0].connected
        is False
    )
    assert config.entry_mode is EntryMode.FIRST
    assert risk_repository.read_risk_config(db_session, account.id, 1) == config
    assert (
        backtest_repository.read_latest_results(db_session, account.id)[1].id
        == second_result.id
    )
    assert first_result.id != second_result.id
    assert (
        lifecycle_link_repository.read_links(db_session, account.id, 1)[0].id == link.id
    )
