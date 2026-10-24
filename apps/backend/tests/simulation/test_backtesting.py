from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from seed import insert_source

from verasig.domain.account import Plan, UserAccount
from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.message import RawTelegramMessage
from verasig.domain.risk_config import RiskConfig
from verasig.domain.signal import EntryType, Side, Signal
from verasig.domain.simulation import Kline
from verasig.features.accounts import repository as account_repository
from verasig.features.feeds import (
    deletion_repository,
    feed_repository,
    message_repository,
)
from verasig.features.mining.mining_confirm import confirm_review
from verasig.features.mining.mining_review import create_review, read_input
from verasig.features.mining.template_mining import mine_template_groups
from verasig.features.provider_scores.scorecard import build_provider_score
from verasig.features.signals import (
    lifecycle_link_repository,
    outcome_repository,
)
from verasig.features.simulation import repository as backtest_repository
from verasig.features.simulation.backtesting import load_folded_signals, run_backtest

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


def _signal() -> Signal:
    return Signal(
        id=_uuid(2),
        channel_id=7,
        message_id=1,
        candidate_text="BTC long entry 100 sl 95 tp 110",
        symbol="BTCUSDT",
        side=Side.LONG,
        entry_type=EntryType.LIMIT_SINGLE,
        entry_low=Decimal("100"),
        entry_high=Decimal("100"),
        stop_loss=Decimal("95"),
        take_profits=[Decimal("110")],
        extracted_at=_BASE,
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


def test_run_backtest_simulates_signals_and_persists_summary(session_factory):
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
        signals = outcome_repository.read_signals(session, 7, account.id)
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


def test_load_folded_signals_uses_stored_deletion_candidacy(session_factory):
    account = _seed(session_factory)
    _insert_deleted_candidate(session_factory, account.id)

    inputs = load_folded_signals(session_factory, account.id, 7)

    # candidacy comes from the stored evidence (miner-set), not a re-derived label
    assert inputs.deletions[0].was_signal_candidate is True


def test_load_folded_signals_honours_manual_lifecycle_link(session_factory):
    # An unthreaded modifier joined to the root by a manual link must fold into the
    # root's timeline — exactly as the signals view does. Before the fix the
    # backtest fold ignored manual links and left the modifier out.
    account = _seed(session_factory)
    modifier = RawTelegramMessage(
        channel_id=7,
        message_id=2,
        text="move SL to BE",
        posted_at=_BASE + timedelta(seconds=30),
        captured_at=_BASE + timedelta(seconds=30),
        has_media=False,
        raw_payload={},
    )
    with session_factory() as session:
        message_repository.insert_messages(session, account.id, [modifier])
        lifecycle_link_repository.insert_link(
            session, account.id, 7, 2, _uuid(2), _BASE + timedelta(seconds=30)
        )
        session.commit()

    inputs = load_folded_signals(session_factory, account.id, 7)

    assert len(inputs.folded_signals) == 1
    assert len(inputs.folded_signals[0].timeline) == 2
    assert inputs.folded_signals[0].timeline[1].source_message_id == 2


def test_backtest_uses_confirmed_review_misses_for_parser_confidence(session_factory):
    account = _seed(session_factory)
    near_miss = RawTelegramMessage(
        channel_id=7,
        message_id=2,
        text="LONG entry 101",
        posted_at=_BASE + timedelta(seconds=30),
        captured_at=_BASE + timedelta(seconds=30),
        has_media=False,
        raw_payload={},
    )
    with session_factory() as session:
        message_repository.insert_messages(session, account.id, [near_miss])
        review_input = read_input(session, account.id, 7)
        groups = mine_template_groups(review_input.messages, review_input.overlay)
        review = create_review(session, account.id, 7, review_input, groups)
        session.commit()
    keys = [group.template_key for group in review.groups]
    confirm_review(session_factory, account.id, 7, review.review_id, keys)

    inputs = load_folded_signals(session_factory, account.id, 7)
    score, explanation = build_provider_score(
        channel=inputs.channel,
        messages=inputs.messages,
        message_count=inputs.message_count,
        events=inputs.signals,
        signals=inputs.signals,
        missed_message_ids=inputs.missed_message_ids,
        deletions=inputs.deletions,
        computed_at=_NOW,
    )
    parser = next(
        component
        for component in explanation.breakdown
        if component.name == "parser_confidence"
    )

    assert inputs.missed_message_ids == [2]
    assert parser.raw_value == 0.5
    assert parser.evidence_refs[-1] == "message:7/2"
    assert score.score < 1.0


def test_confirmed_misses_survive_a_stale_review(session_factory):
    # New messages make the confirmed review stale; its misses still pair with
    # the stored signals, so parser confidence must not jump to a perfect 1.0.
    account = _seed(session_factory)
    near_miss = RawTelegramMessage(
        channel_id=7,
        message_id=2,
        text="LONG entry 101",
        posted_at=_BASE + timedelta(seconds=30),
        captured_at=_BASE + timedelta(seconds=30),
        has_media=False,
        raw_payload={},
    )
    later = RawTelegramMessage(
        channel_id=7,
        message_id=3,
        text="gm",
        posted_at=_BASE + timedelta(minutes=5),
        captured_at=_BASE + timedelta(minutes=5),
        has_media=False,
        raw_payload={},
    )
    with session_factory() as session:
        message_repository.insert_messages(session, account.id, [near_miss])
        review_input = read_input(session, account.id, 7)
        groups = mine_template_groups(review_input.messages, review_input.overlay)
        review = create_review(session, account.id, 7, review_input, groups)
        session.commit()
    keys = [group.template_key for group in review.groups]
    confirm_review(session_factory, account.id, 7, review.review_id, keys)
    with session_factory() as session:
        message_repository.insert_messages(session, account.id, [later])
        session.commit()

    inputs = load_folded_signals(session_factory, account.id, 7)

    assert inputs.missed_message_ids == [2]


def _seed(session_factory) -> UserAccount:
    with session_factory() as session:
        account = account_repository.insert_account(session, _account())
        insert_source(session, account.id)
        feed_repository.create_feed(session, account.id, _channel(), _BASE)
        message_repository.insert_messages(session, account.id, [_message()])
        outcome_repository.insert_signals(session, [_signal()], account.id)
        session.commit()
        return account


def _insert_deleted_candidate(session_factory, user_id: UUID) -> None:
    with session_factory() as session:
        deletion_repository.upsert_deletion_evidence(
            session,
            user_id,
            [
                DeletedSignalEvidence(
                    channel_id=7,
                    message_id=1,
                    confidence=DeletionConfidence.CONFIRMED,
                    method=DeletionMethod.SNAPSHOT_DIFF,
                    detected_at=_BASE,
                    was_signal_candidate=True,
                )
            ],
        )
        session.commit()
