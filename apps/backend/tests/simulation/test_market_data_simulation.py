import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from verasig.domain.channel import TelegramChannel
from verasig.domain.lifecycle import FoldedSignal, FoldStep
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import EntryType, Side, Signal, SignalEventType
from verasig.domain.simulation import Kline, SimOutcomeKind
from verasig.features.provider_scores.scorecard import build_provider_score
from verasig.features.simulation.simulator import simulate_outcomes_from_market_data
from verasig.foundation.market_data.bybit_market_data import (
    BYBIT_KLINE_LIMIT,
    BybitApiError,
    BybitKlineClient,
)

_BASE = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)
_END = _BASE + timedelta(minutes=2)
# relative to this file, not the cwd, so the test runs from any directory
_FIXTURE = Path(__file__).parent.parent / "fixtures" / "klines" / "btcusdt_known_r.json"


class FakeMarketData:
    def __init__(self, klines: list[Kline]) -> None:
        self._klines = klines
        self.calls: list[tuple[str, datetime, datetime, str]] = []

    def klines(
        self, symbol: str, start: datetime, end: datetime, interval: str = "1"
    ) -> list[Kline]:
        self.calls.append((symbol, start, end, interval))
        return list(self._klines)


def _uuid(suffix: int) -> UUID:
    return UUID(f"40000000-0000-0000-0000-{suffix:012d}")


def _load_klines() -> list[Kline]:
    return [Kline.model_validate(item) for item in json.loads(_FIXTURE.read_text())]


def _folded(signal_id: UUID, at: datetime = _BASE) -> FoldedSignal:
    return FoldedSignal(
        root_signal_id=signal_id,
        symbol="BTCUSDT",
        side=Side.LONG,
        timeline=[
            FoldStep(
                at=at,
                source_signal_id=signal_id,
                source_message_id=1,
                event_type=SignalEventType.NEW_ENTRY,
                effective_stop_loss=Decimal("95"),
                effective_take_profits=[Decimal("110")],
                effective_size=Decimal(1),
                effective_entry=Decimal("100"),
                leg_size=Decimal(1),
                leg_price=Decimal("100"),
            )
        ],
    )


def _channel() -> TelegramChannel:
    return TelegramChannel(
        channel_id=7,
        handle="pilot",
        title="Pilot",
        is_private=False,
        subscriber_count=None,
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
        raw_payload={"id": 1},
    )


def _signal(signal_id: UUID) -> Signal:
    return Signal(
        id=signal_id,
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


def test_market_data_backed_simulation_feeds_scorecard_components():
    signal_id = _uuid(1)
    market_data = FakeMarketData(_load_klines())

    outcomes = simulate_outcomes_from_market_data(
        folded_signals=[_folded(signal_id)],
        market_data=market_data,
        end=_END,
    )
    signal = _signal(signal_id)
    score, explanation = build_provider_score(
        channel=_channel(),
        messages=[_message()],
        message_count=1,
        events=[signal],
        signals=[signal],
        missed_message_ids=[],
        deletions=[],
        sim_outcomes=outcomes,
        computed_at=_BASE,
    )

    assert market_data.calls == [("BTCUSDT", _BASE, _END, "1")]
    assert outcomes[0].r_multiple == pytest.approx(2.0)
    assert outcomes[0].mae == pytest.approx(0.2)
    assert score.simulated_count == 1
    assert [component.name for component in score.components[:2]] == [
        "sim_expectancy",
        "drawdown",
    ]
    assert score.components[0].raw_value == pytest.approx(2.0)
    assert score.components[1].raw_value == pytest.approx(0.2)
    assert "sim_expectancy: simulation not supplied" not in explanation.notes
    assert "drawdown: simulation not supplied" not in explanation.notes


def test_signals_on_one_symbol_share_one_kline_fetch():
    market_data = FakeMarketData(_load_klines())
    later = _BASE + timedelta(minutes=1)

    outcomes = simulate_outcomes_from_market_data(
        folded_signals=[_folded(_uuid(1), at=later), _folded(_uuid(2))],
        market_data=market_data,
        end=_END,
    )

    # one fetch from the earliest entry; each signal replays from its own entry
    assert market_data.calls == [("BTCUSDT", _BASE, _END, "1")]
    assert outcomes[1].r_multiple == pytest.approx(2.0)
    # the later signal never sees the 12:00 bar whose 99 low reached its entry
    assert outcomes[0].kind is SimOutcomeKind.UNFILLED


def _bybit_page(open_times_ms: list[int]) -> dict:
    rows = [[str(ms), "100", "101", "99", "100", "1", "1"] for ms in open_times_ms]
    return {
        "retCode": 0,
        "retMsg": "OK",
        "result": {"symbol": "BTCUSDT", "list": list(reversed(rows))},
    }


def _bybit_client(handler) -> BybitKlineClient:
    return BybitKlineClient(
        http_client=httpx.Client(
            base_url="https://api.bybit.test", transport=httpx.MockTransport(handler)
        )
    )


def test_bybit_client_pages_back_until_the_window_start():
    minute = 60_000
    start_ms = 1_700_000_000_000
    total = BYBIT_KLINE_LIMIT + 5
    all_bars = [start_ms + index * minute for index in range(total)]
    ends: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        end_ms = int(request.url.params["end"])
        ends.append(end_ms)
        window = [ms for ms in all_bars if ms <= end_ms][-BYBIT_KLINE_LIMIT:]
        return httpx.Response(200, json=_bybit_page(window))

    klines = _bybit_client(handler).klines(
        "BTCUSDT",
        datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc),
        datetime.fromtimestamp(all_bars[-1] / 1000, tz=timezone.utc),
    )

    assert len(ends) == 2
    assert ends[1] == all_bars[5] - 1
    assert len(klines) == total
    assert [kline.open_time for kline in klines] == sorted(
        kline.open_time for kline in klines
    )


def test_bybit_client_raises_on_a_non_zero_ret_code():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"retCode": 10001, "retMsg": "params error", "result": {}}
        )

    with pytest.raises(BybitApiError, match="10001"):
        _bybit_client(handler).klines("BTCUSDT", _BASE, _END)
