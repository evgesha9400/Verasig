from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from conftest import _auth
from conftest import _register_user as _register
from seed import insert_source

from verasig.domain.channel import TelegramChannel
from verasig.domain.deletion import (
    DeletedSignalEvidence,
    DeletionConfidence,
    DeletionMethod,
)
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import EntryType, Side, Signal
from verasig.domain.simulation import Kline
from verasig.features.feeds import (
    deletion_repository,
    feed_repository,
    message_repository,
)
from verasig.features.signals import outcome_repository
from verasig.features.simulation import repository as backtest_repository

_BASE = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)
_SIGNAL_ID = UUID("70000000-0000-0000-0000-000000000002")


class FakeMarketData:
    def klines(
        self, _symbol: str, _start: datetime, _end: datetime, _interval: str = "1"
    ) -> list[Kline]:
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


def test_backtest_job_streams_phases_persists_outcomes_and_updates_chat(client, app):
    token, user_id = _register(client)
    _seed(app, user_id)
    app.state.market_data_factory = FakeMarketData

    started = client.post("/feeds/7/backtest", headers=_auth(token))
    with client.stream(
        "GET", "/feeds/7/backtest/progress", headers=_auth(token)
    ) as response:
        body = "".join(response.iter_text())
    listed = client.get("/feeds", headers=_auth(token))
    row = _latest_backtest(app, user_id)

    _seed_confirmed_signal_deletion(app, user_id)
    deletion_listed = client.get("/feeds", headers=_auth(token))

    assert started.status_code == 202
    assert response.status_code == 200
    assert "Replaying historical signals" in body
    assert "Applying your risk model" in body
    assert "Simulating fills & slippage" in body
    assert "Scoring confidence & drawdown" in body
    assert "event: done" in body
    assert '"winRate": 100.0' in body
    assert listed.json()["feeds"][0]["status"] == "analyzed"
    assert listed.json()["feeds"][0]["score"] is not None
    assert len(row.outcomes) == 1
    assert row.outcomes[0]["pctReturn"] == 1.0
    assert deletion_listed.json()["feeds"][0]["score"] == 0


def test_backtest_requires_a_verified_feed(client, app):
    token, user_id = _register(client)
    _seed(app, user_id)
    with app.state.session_factory() as session:
        feed_repository.set_status(session, user_id, 7, "backfilled")
        session.commit()
    app.state.market_data_factory = FakeMarketData

    response = client.post("/feeds/7/backtest", headers=_auth(token))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "FEED_NOT_VERIFIED"


def test_backtest_foreign_user_is_not_found(client, app):
    owner, owner_id = _register(client, "owner@example.com")
    other, _other_id = _register(client, "other@example.com")
    _seed(app, owner_id)

    response = client.post("/feeds/7/backtest", headers=_auth(other))

    assert owner
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FEED_NOT_FOUND"


def test_backtest_progress_reports_missing_job_as_404(client, app):
    token, user_id = _register(client)
    _seed(app, user_id)

    response = client.get("/feeds/7/backtest/progress", headers=_auth(token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"


def _seed(app, user_id: UUID) -> None:
    with app.state.session_factory() as session:
        insert_source(session, user_id)
        feed_repository.create_feed(
            session,
            user_id,
            TelegramChannel(
                channel_id=7,
                handle="pilot",
                title="Pilot",
                is_private=False,
                subscriber_count=1234,
                first_seen_at=_BASE,
            ),
            _BASE,
        )
        message_repository.insert_messages(
            session,
            user_id,
            [
                RawTelegramMessage(
                    channel_id=7,
                    message_id=1,
                    text="BTC long entry 100 sl 95 tp 110",
                    posted_at=_BASE,
                    captured_at=_BASE,
                    has_media=False,
                    raw_payload={},
                )
            ],
        )
        outcome_repository.insert_signals(session, [_signal()], user_id)
        feed_repository.set_status(session, user_id, 7, "verified")
        session.commit()


def _signal() -> Signal:
    return Signal(
        id=_SIGNAL_ID,
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


def _latest_backtest(app, user_id: UUID):
    with app.state.session_factory() as session:
        row = backtest_repository.read_latest_results(session, user_id)[7]
        session.expunge(row)
        return row


def _seed_confirmed_signal_deletion(app, user_id: UUID) -> None:
    with app.state.session_factory() as session:
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
