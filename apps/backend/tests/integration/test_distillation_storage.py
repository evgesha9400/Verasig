from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.drift import FilterDriftWarning, MissDiscoveredBy
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel, LabelKind
from verasig.domain.message import RawTelegramMessage
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import ExtractedSignal, Side
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import (
    feed_repository,
    message_repository,
)
from verasig.features.rules import drift_repository
from verasig.features.rules import repository as rule_repository
from verasig.features.signals import event_repository, outcome_repository


def _instant() -> datetime:
    return datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)


def _channel() -> TelegramChannel:
    return TelegramChannel(
        channel_id=7,
        handle="pilot",
        title="Pilot",
        is_private=False,
        first_seen_at=_instant(),
    )


def _account() -> UserAccount:
    return UserAccount(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        password_hash="hash",
        first_name="Ada",
        last_name="Lovelace",
        plan=Plan.OBSERVER,
        pending_email=None,
        cancel_at=None,
        created_at=_instant(),
    )


def _seed_feed_with_messages(session_factory, message_ids: list[int]) -> UUID:
    """Seed account + feed + messages; return the owning user_id."""
    with session_factory() as session:
        account = account_repository.insert_account(session, _account())
        insert_source(session, account.id)
        feed_repository.create_feed(session, account.id, _channel(), _instant())
        message_repository.insert_messages(
            session,
            account.id,
            [
                RawTelegramMessage(
                    channel_id=7,
                    message_id=mid,
                    text=f"msg {mid}",
                    posted_at=_instant(),
                    captured_at=_instant(),
                    has_media=False,
                    raw_payload={"id": mid},
                )
                for mid in message_ids
            ],
        )
        session.commit()
    return account.id


def _event(message_id: int, **overrides) -> RawSignalEvent:
    base = dict(
        channel_id=7,
        message_id=message_id,
        candidate_text=f"BTC long {message_id}",
        materialized_by=MaterializationPath.SEED_HEURISTIC,
    )
    base.update(overrides)
    return RawSignalEvent(**base)


def test_signal_events_persist_idempotently_and_read_back(session_factory):
    user_id = _seed_feed_with_messages(session_factory, [1, 2, 3])
    with session_factory() as session:
        first = event_repository.insert_signal_events(
            session, user_id, [_event(1), _event(2)]
        )
        session.commit()
        again = event_repository.insert_signal_events(
            session, user_id, [_event(2), _event(3)]
        )
        session.commit()
    assert (first, again) == (2, 1)  # idempotent on (channel_id, message_id)
    with session_factory() as session:
        events = event_repository.read_signal_events(session, user_id, 7)
    assert {e.message_id for e in events} == {1, 2, 3}
    assert all(e.materialized_by is MaterializationPath.SEED_HEURISTIC for e in events)


def test_filter_rule_upserts_and_reads_back(session_factory):
    user_id = _seed_feed_with_messages(session_factory, [1])
    rule = FilterRule(
        rule_id="7-filter-v1",
        user_id=user_id,
        channel_id=7,
        include_patterns=[r"(?i)\blong\b"],
    )
    with session_factory() as session:
        rule_repository.upsert_filter_rule(session, rule)
        session.commit()
    with session_factory() as session:
        rules = rule_repository.read_filter_rules(session, 7, user_id)
    assert len(rules) == 1
    assert rules[0].rule_id == "7-filter-v1"
    assert rules[0].include_patterns == [r"(?i)\blong\b"]


def test_parser_rules_upsert_and_read_back_with_side_aliases(session_factory):
    user_id = _seed_feed_with_messages(session_factory, [1])
    rule = ParserRule(
        rule_id="7-parser-1-v1",
        user_id=user_id,
        channel_id=7,
        patterns=[r"(?P<symbol>BTC)"],
        field_map={"symbol": "symbol"},
        side_aliases={"long": "LONG"},
    )
    with session_factory() as session:
        rule_repository.upsert_parser_rules(session, [rule])
        session.commit()
    with session_factory() as session:
        rules = rule_repository.read_parser_rules(session, 7, user_id)
    assert rules[0].side_aliases["long"] is Side.LONG


def test_golden_labels_upsert_overwrites_and_round_trips_expected(session_factory):
    user_id = _seed_feed_with_messages(session_factory, [1])
    expected = ExtractedSignal(
        event_id=_event(1).id,
        channel_id=7,
        symbol="BTCUSDT",
        side=Side.LONG,
        stop_loss=Decimal("64000"),
        take_profits=[Decimal("67000")],
    )
    with session_factory() as session:
        rule_repository.upsert_labels(
            session,
            [
                GoldenLabel(
                    user_id=user_id,
                    channel_id=7,
                    message_id=1,
                    label=LabelKind.NOISE,
                )
            ],
        )
        session.commit()
        rule_repository.upsert_labels(
            session,
            [
                GoldenLabel(
                    user_id=user_id,
                    channel_id=7,
                    message_id=1,
                    label=LabelKind.SIGNAL,
                    expected=expected,
                )
            ],
        )
        session.commit()
    with session_factory() as session:
        labels = rule_repository.read_labels(session, 7, user_id)
    assert len(labels) == 1  # re-label overwrote, not duplicated
    assert labels[0].is_signal is True
    assert labels[0].expected.symbol == "BTCUSDT"
    assert labels[0].expected.take_profits == [Decimal("67000")]


def test_drift_warnings_persist_idempotently(session_factory):
    user_id = _seed_feed_with_messages(session_factory, [5])
    warning = FilterDriftWarning(
        channel_id=7,
        message_id=5,
        miss_discovered_by=MissDiscoveredBy.PARSER_BACKFILL,
    )
    with session_factory() as session:
        first = drift_repository.insert_drift_warnings(session, [warning], user_id)
        session.commit()
        again = drift_repository.insert_drift_warnings(
            session,
            [
                FilterDriftWarning(
                    channel_id=7,
                    message_id=5,
                    miss_discovered_by=MissDiscoveredBy.HUMAN_AUDIT,
                )
            ],
            user_id,
        )
        session.commit()
    assert (first, again) == (1, 0)  # one drift per missed (channel, message)
    with session_factory() as session:
        warnings = drift_repository.read_drift_warnings(session, 7, user_id)
    assert len(warnings) == 1
    assert warnings[0].miss_discovered_by is MissDiscoveredBy.PARSER_BACKFILL


def test_read_messages_returns_domain_messages(session_factory):
    user_id = _seed_feed_with_messages(session_factory, [1, 2])
    with session_factory() as session:
        messages = message_repository.read_messages(session, user_id, 7)
    assert {m.message_id for m in messages} == {1, 2}
    assert all(isinstance(m, RawTelegramMessage) for m in messages)


def test_extracted_and_unrecognized_signals_persist(session_factory):
    user_id = _seed_feed_with_messages(session_factory, [1, 2])
    with session_factory() as session:
        event_repository.insert_signal_events(session, user_id, [_event(1), _event(2)])
        session.commit()
        events = event_repository.read_signal_events(session, user_id, 7)
        by_message = {e.message_id: e for e in events}
        signal = ExtractedSignal(
            event_id=by_message[1].id,
            channel_id=7,
            symbol="BTCUSDT",
            side=Side.LONG,
            take_profits=[Decimal("67000")],
        )
        outcome_repository.insert_extracted_signals(session, [signal], user_id)
        session.commit()
    with session_factory() as session:
        stored = outcome_repository.read_extracted_signals(session, 7, user_id)
    assert stored[0].symbol == "BTCUSDT"
    assert stored[0].take_profits == [Decimal("67000")]
