from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from typer.testing import CliRunner

from verasig.cli import app
from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import EntryType, ExtractedSignal, Side
from verasig.domain.simulation import Kline
from verasig.storage import repositories as repo

runner = CliRunner()

_CHANNEL_ID = 7
_BASE = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _uuid(suffix: int) -> UUID:
    return UUID(f"30000000-0000-0000-0000-{suffix:012d}")


def _message(message_id: int):
    return RawTelegramMessage(
        channel_id=_CHANNEL_ID,
        message_id=message_id,
        text=(
            "BTC long market sl 64000 tp 67000"
            if message_id == 1
            else f"message {message_id}"
        ),
        posted_at=_BASE,
        captured_at=_BASE,
        has_media=False,
        views=1000 + message_id,
        forwards=100 + message_id,
        raw_payload={"id": message_id},
    )


def _seed_score(session_factory) -> None:
    event = RawSignalEvent(
        id=_uuid(1),
        channel_id=_CHANNEL_ID,
        message_id=1,
        candidate_text="BTC long entry 65000 sl 64000 tp 67000",
        materialized_by=MaterializationPath.SEED_HEURISTIC,
        created_at=_BASE,
    )
    with session_factory() as session:
        repo.upsert_channel(
            session,
            TelegramChannel(
                channel_id=_CHANNEL_ID,
                handle="pilot",
                title="Pilot",
                is_private=False,
                subscriber_count=5000,
                first_seen_at=_BASE,
            ),
        )
        repo.insert_messages(session, [_message(1), _message(2)])
        repo.insert_signal_events(session, [event])
        repo.insert_extracted_signals(
            session,
            [
                ExtractedSignal(
                    id=_uuid(2),
                    event_id=event.id,
                    channel_id=_CHANNEL_ID,
                    symbol="BTCUSDT",
                    side=Side.LONG,
                    entry_type=EntryType.MARKET,
                    stop_loss="64000",
                    take_profits=["67000"],
                    extracted_at=_BASE,
                )
            ],
        )
        repo.upsert_deletion_evidence(
            session,
            [
                DeletedSignalEvidence(
                    id=_uuid(3),
                    channel_id=_CHANNEL_ID,
                    message_id=99,
                    confidence=DeletionConfidence.CONFIRMED,
                    method=DeletionMethod.SNAPSHOT_DIFF,
                    detected_at=_BASE,
                    was_signal_candidate=False,
                )
            ],
        )
        session.commit()


class FakeMarketData:
    def __init__(self) -> None:
        self.calls: list[tuple[str, datetime, datetime, str]] = []

    def klines(
        self, symbol: str, start: datetime, end: datetime, interval: str = "1"
    ) -> list[Kline]:
        self.calls.append((symbol, start, end, interval))
        return [
            Kline(
                symbol=symbol,
                open_time=start,
                open=Decimal("65000"),
                high=Decimal("67000"),
                low=Decimal("65000"),
                close=Decimal("67000"),
                volume=Decimal("1"),
            )
        ]


def test_score_cli_prints_scorecard_and_explanation(
    session_factory, monkeypatch, pg_url
):
    _seed_score(session_factory)
    monkeypatch.setenv("VERASIG_DATABASE_URL_OVERRIDE", pg_url)

    result = runner.invoke(app, ["score", "@pilot"])

    assert result.exit_code == 0
    output = result.output
    assert "ProviderScore Pilot @pilot id=7" in output
    assert "score=0.5000" in output
    assert "weights=v0" in output
    assert "signals=1" in output
    assert "simulated=0" in output
    assert (
        "deletion_behaviour raw=1.0000 normalized=1.0000 "
        "weight=0.2000 contribution=0.2000" in output
    )
    assert "active_user_proxy raw=5000.0000" in output
    assert "Notes:" in output
    assert "sim_expectancy: pending Slice 9 simulation" in output
    assert "drawdown: pending Slice 9 simulation" in output
    assert "active_user_proxy: proxy only, not a quality claim" in output


def test_score_cli_unknown_channel_exits_nonzero(monkeypatch, pg_url):
    monkeypatch.setenv("VERASIG_DATABASE_URL_OVERRIDE", pg_url)

    result = runner.invoke(app, ["score", "@ghost"])

    assert result.exit_code == 1


def test_score_cli_can_include_simulation_from_market_data(
    session_factory, monkeypatch, pg_url
):
    _seed_score(session_factory)
    market_data = FakeMarketData()
    monkeypatch.setenv("VERASIG_DATABASE_URL_OVERRIDE", pg_url)
    monkeypatch.setattr("verasig.cli._make_market_data", lambda: market_data)

    result = runner.invoke(
        app,
        ["score", "@pilot", "--simulate", "--until", "2026-06-06T12:01:00+00:00"],
    )

    assert result.exit_code == 0
    output = result.output
    assert market_data.calls == [
        (
            "BTCUSDT",
            _BASE,
            datetime(2026, 6, 6, 12, 1, tzinfo=timezone.utc),
            "1",
        )
    ]
    assert "simulated=1" in output
    assert (
        "sim_expectancy raw=2.0000 normalized=1.0000 "
        "weight=0.3000 contribution=0.3000" in output
    )
    assert (
        "drawdown raw=0.0000 normalized=1.0000 "
        "weight=0.2000 contribution=0.2000" in output
    )
    assert "sim_expectancy: pending Slice 9 simulation" not in output
    assert "drawdown: pending Slice 9 simulation" not in output
