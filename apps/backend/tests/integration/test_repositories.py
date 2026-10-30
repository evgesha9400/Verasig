from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage
from verasig.domain.risk_config import EntryMode, RiskConfig
from verasig.domain.signal import Side, Signal
from verasig.features.accounts import repository as account_repository
from verasig.features.exchanges import repository as exchange_repository
from verasig.features.feeds import (
    feed_repository,
    message_repository,
)
from verasig.features.feeds.history_depth import HistoryDepth
from verasig.features.risk import repository as risk_repository
from verasig.features.signals import (
    lifecycle_link_repository,
    outcome_repository,
)
from verasig.features.simulation import repository as backtest_repository
from verasig.features.sources import source_repository
from verasig.storage.models import FeedRow


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
        plan=Plan.FREE,
        pending_email=None,
        cancel_at=None,
        created_at=_instant(),
    )


def test_insert_messages_dedups_on_conflict(db_session):
    account = account_repository.insert_account(db_session, _account())
    insert_source(db_session, account.id)
    feed_repository.create_feed(db_session, account.id, _channel(), _instant())
    db_session.commit()
    inserted_first = message_repository.insert_messages(
        db_session, account.id, [_message(1), _message(2)]
    )
    db_session.commit()
    inserted_again = message_repository.insert_messages(
        db_session, account.id, [_message(2), _message(3)]
    )
    db_session.commit()
    assert inserted_first == 2
    assert inserted_again == 1
    assert message_repository.count_messages(db_session, account.id, 1) == 3


def test_advance_cursor_is_monotonic(db_session):
    account = account_repository.insert_account(db_session, _account())
    insert_source(db_session, account.id)
    feed_repository.create_feed(db_session, account.id, _channel(), _instant())
    db_session.commit()
    feed_repository.advance_cursor(db_session, account.id, 1, 50)
    db_session.commit()
    feed_repository.advance_cursor(db_session, account.id, 1, 30)
    db_session.commit()
    assert feed_repository.read_cursor(db_session, account.id, 1) == 50


def test_read_cursor_is_none_for_unknown_channel(db_session):
    assert feed_repository.read_cursor(db_session, uuid4(), 999) is None


def test_advance_cursor_is_a_noop_for_a_missing_feed(db_session):
    # a feed deleted mid-backfill must not raise on the trailing cursor advance.
    feed_repository.advance_cursor(db_session, uuid4(), 999, 50)  # no feed row
    assert feed_repository.read_cursor(db_session, uuid4(), 999) is None


def test_upsert_feed_refreshes_metadata_but_preserves_first_seen_and_cursor(
    db_session,
):
    account = account_repository.insert_account(db_session, _account())
    insert_source(db_session, account.id)
    feed_repository.create_feed(
        db_session, account.id, _channel(subscriber_count=100), _instant()
    )
    db_session.commit()
    feed_repository.advance_cursor(db_session, account.id, 1, 42)
    db_session.commit()

    later = datetime(2027, 1, 1, tzinfo=timezone.utc)
    feed_repository.upsert_feed_metadata(
        db_session,
        account.id,
        _channel(title="Renamed", subscriber_count=200, first_seen_at=later),
        _instant(),
    )
    db_session.commit()

    feed = db_session.get(FeedRow, (account.id, 1))
    assert feed.title == "Renamed"
    assert feed.meta["subscriber_count"] == 200
    assert feed.first_seen_at == _instant()
    assert feed_repository.read_cursor(db_session, account.id, 1) == 42


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
    applied = account_repository.apply_pending_email(
        db_session, account.id, "next@example.com"
    )

    assert renamed.first_name == "Grace"
    assert pending.pending_email == "next@example.com"
    assert applied.email == "next@example.com"


def test_apply_pending_email_refuses_a_replaced_pending_email(db_session):
    account = account_repository.insert_account(db_session, _account())
    account_repository.set_pending_email(db_session, account.id, "first@example.com")
    # the pending address changed after the caller checked it (TOCTOU)
    account_repository.set_pending_email(db_session, account.id, "second@example.com")

    applied = account_repository.apply_pending_email(
        db_session, account.id, "first@example.com"
    )

    assert applied is None
    unchanged = account_repository.find_by_id(db_session, account.id)
    assert unchanged.email == "user@example.com"
    assert unchanged.pending_email == "second@example.com"


def test_source_repository_round_trips_status_config_and_delete(db_session):
    account = account_repository.insert_account(db_session, _account())
    db_session.commit()

    pending = source_repository.create_source(
        db_session,
        account.id,
        "Telegram",
        "pending",
        {"api_id": 123, "phone": "+15551234567"},
        _instant(),
    )
    db_session.commit()
    assert pending.status == "pending"
    assert pending.config_encrypted == {"api_id": 123, "phone": "+15551234567"}

    connected = source_repository.set_status(
        db_session, account.id, "Telegram", "connected"
    )
    db_session.commit()
    assert connected.status == "connected"
    assert (
        source_repository.read_source(
            db_session, account.id, "Telegram"
        ).config_encrypted["phone"]
        == "+15551234567"
    )

    source_repository.delete_source(db_session, account.id, "Telegram")
    db_session.commit()
    assert source_repository.read_source(db_session, account.id, "Telegram") is None


def test_feed_repository_round_trips_and_purges_capture_on_delete(db_session):
    account = account_repository.insert_account(db_session, _account())
    insert_source(db_session, account.id)
    feed = feed_repository.create_feed(db_session, account.id, _channel(), _instant())
    message_repository.insert_messages(db_session, account.id, [_message(99)])
    feed_repository.advance_cursor(db_session, account.id, 1, 99)
    db_session.commit()

    assert feed.status == "new"
    assert feed_repository.count_feeds(db_session, account.id) == 1
    assert (
        feed_repository.set_status(db_session, account.id, 1, "verified").status
        == "verified"
    )

    feed_repository.delete_feed(db_session, account.id, 1)
    db_session.commit()

    assert feed_repository.read_feed(db_session, account.id, 1) is None
    assert message_repository.count_messages(db_session, account.id, 1) == 0
    assert feed_repository.read_cursor(db_session, account.id, 1) is None


def test_feed_defaults_to_one_year_history_depth(db_session):
    account = account_repository.insert_account(db_session, _account())
    insert_source(db_session, account.id)
    feed_repository.create_feed(db_session, account.id, _channel(), _instant())
    db_session.commit()

    assert (
        feed_repository.read_history_depth(db_session, account.id, 1)
        is HistoryDepth.ONE_YEAR
    )


def test_set_history_depth_round_trips(db_session):
    account = account_repository.insert_account(db_session, _account())
    insert_source(db_session, account.id)
    feed_repository.create_feed(db_session, account.id, _channel(), _instant())
    db_session.commit()

    feed_repository.set_history_depth(
        db_session, account.id, 1, HistoryDepth.SIX_MONTHS
    )
    db_session.commit()

    assert (
        feed_repository.read_history_depth(db_session, account.id, 1)
        is HistoryDepth.SIX_MONTHS
    )


def test_upsert_feed_metadata_preserves_history_depth(db_session):
    account = account_repository.insert_account(db_session, _account())
    insert_source(db_session, account.id)
    feed_repository.create_feed(db_session, account.id, _channel(), _instant())
    feed_repository.set_history_depth(db_session, account.id, 1, HistoryDepth.ALL)
    db_session.commit()

    feed_repository.upsert_feed_metadata(
        db_session, account.id, _channel(title="Renamed"), _instant()
    )
    db_session.commit()

    assert (
        feed_repository.read_history_depth(db_session, account.id, 1)
        is HistoryDepth.ALL
    )


def test_exchange_risk_backtest_and_lifecycle_repositories_round_trip(db_session):
    account = account_repository.insert_account(db_session, _account())
    insert_source(db_session, account.id)
    feed_repository.create_feed(db_session, account.id, _channel(), _instant())
    message_repository.insert_messages(db_session, account.id, [_message(77)])
    signal = Signal(
        channel_id=1,
        message_id=77,
        candidate_text="BTC long",
        symbol="BTCUSDT",
        side=Side.LONG,
    )
    outcome_repository.insert_signals(db_session, [signal], account.id)
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
        db_session, account.id, 1, 77, signal.id, _instant()
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
