from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.message import RawTelegramMessage
from verasig.domain.parser_rule import ParserRule
from verasig.domain.risk_config import RiskConfig
from verasig.domain.simulation import Kline
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import (
    feed_repository,
    message_repository,
)
from verasig.features.rules import repository as rule_repository
from verasig.features.signals import event_repository, outcome_repository
from verasig.features.simulation import repository as backtest_repository
from verasig.features.simulation.backtesting import run_backtest

_BASE = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)
_NOW = _BASE + timedelta(minutes=2)


class FakeMarketData:
    def __init__(self, klines: list[Kline]) -> None:
        self.klines_by_symbol = {"BTCUSDT": klines}
        self.calls: list[tuple[str, datetime, datetime, str]] = []

    def klines(
        self, symbol: str, start: datetime, end: datetime, interval: str = "1"
    ) -> list[Kline]:
        self.calls.append((symbol, start, end, interval))
        return self.klines_by_symbol[symbol]


def _uuid(suffix: int) -> UUID:
    return UUID(f"50000000-0000-0000-0000-{suffix:012d}")


def _account() -> UserAccount:
    return UserAccount(
        id=uuid4(),
        email="user@example.com",
        password_hash="hash",
        first_name="Ada",
        last_name="Lovelace",
        plan=Plan.OPERATOR,
        pending_email=None,
        cancel_at=None,
        created_at=_BASE,
    )


def _channel() -> TelegramChannel:
    return TelegramChannel(
        channel_id=7,
        handle="pilot",
        title="Pilot",
        is_private=False,
        subscriber_count=1234,
        first_seen_at=_BASE,
    )


def _message() -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=7,
        message_id=1,
        text="BTC long entry 100 sl 95 tp 110",
        posted_at=_BASE,
        captured_at=_BASE,
        has_media=False,
        raw_payload={},
    )


def _event() -> RawSignalEvent:
    return RawSignalEvent(
        id=_uuid(1),
        channel_id=7,
        message_id=1,
        candidate_text="BTC long entry 100 sl 95 tp 110",
        materialized_by=MaterializationPath.SEED_HEURISTIC,
        created_at=_BASE,
    )


def _parser_rule(user_id: UUID) -> ParserRule:
    return ParserRule(
        rule_id=f"{user_id}:7-parser-v1",
        user_id=user_id,
        channel_id=7,
        patterns=[
            r"(?P<symbol>[A-Z]{2,10})\s+(?P<side>long|short)"
            r".*?entry\s+(?P<entry>[\d.]+).*?sl\s+(?P<sl>[\d.]+)"
            r".*?tp\s+(?P<tp>[\d.]+)"
        ],
        field_map={
            "symbol": "symbol",
            "side": "side",
            "entry": "entry",
            "sl": "stop_loss",
            "tp": "take_profit",
        },
        side_aliases={"long": "LONG", "short": "SHORT"},
    )


def _klines() -> list[Kline]:
    return [
        Kline(
            symbol="BTCUSDT",
            open_time=_BASE,
            open=Decimal("100"),
            high=Decimal("104"),
            low=Decimal("99"),
            close=Decimal("102"),
            volume=Decimal("1"),
        ),
        Kline(
            symbol="BTCUSDT",
            open_time=_BASE + timedelta(minutes=1),
            open=Decimal("102"),
            high=Decimal("111"),
            low=Decimal("101"),
            close=Decimal("110"),
            volume=Decimal("1"),
        ),
    ]


def test_run_backtest_extracts_missing_candidates_and_persists_summary(session_factory):
    account = _seed(session_factory)
    market_data = FakeMarketData(_klines())

    summary = run_backtest(
        session_factory,
        account.id,
        7,
        market_data,
        RiskConfig(),
        _NOW,
    )

    with session_factory() as session:
        result = backtest_repository.read_latest_results(session, account.id)[7]
        signals = outcome_repository.read_extracted_signals(session, 7, account.id)
        subscription = feed_repository.read_feed(session, account.id, 7)

    assert market_data.calls == [("BTCUSDT", _BASE, _NOW, "1")]
    assert len(signals) == 1
    assert summary.win_rate == 100.0
    assert summary.pnl == 1.0
    assert len(summary.outcomes) == 1
    assert result.outcomes[0]["rootSignalId"] == str(
        summary.outcomes[0].folded_signal_id
    )
    assert result.outcomes[0]["pctReturn"] == 1.0
    assert subscription.status == "analyzed"


def _seed(session_factory) -> UserAccount:
    with session_factory() as session:
        account = account_repository.insert_account(session, _account())
        insert_source(session, account.id)
        feed_repository.create_feed(session, account.id, _channel(), _BASE)
        message_repository.insert_messages(session, account.id, [_message()])
        event_repository.insert_signal_events(session, account.id, [_event()])
        rule_repository.upsert_parser_rules(session, [_parser_rule(account.id)])
        session.commit()
        return account
