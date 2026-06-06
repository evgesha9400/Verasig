from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from verasig.domain.lifecycle import FoldedSignal, FoldStep
from verasig.domain.signal import Side, SignalEventType
from verasig.domain.simulation import Kline, SimOutcomeKind
from verasig.services.scoring.policies import ProviderStatedPolicy

_BASE = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _step(**overrides) -> FoldStep:
    base = {
        "at": _BASE,
        "source_signal_id": uuid4(),
        "source_message_id": 1,
        "event_type": SignalEventType.NEW_ENTRY,
        "effective_stop_loss": Decimal("95"),
        "effective_take_profits": [Decimal("110")],
        "effective_size": Decimal(1),
        "effective_entry": Decimal("100"),
        "leg_size": Decimal(1),
        "leg_price": Decimal("100"),
    }
    base.update(overrides)
    return FoldStep(**base)


def _folded(**overrides) -> FoldedSignal:
    base = {
        "root_signal_id": uuid4(),
        "symbol": "BTCUSDT",
        "side": Side.LONG,
        "timeline": [_step()],
    }
    base.update(overrides)
    return FoldedSignal(**base)


def _bar(**overrides) -> Kline:
    base = {
        "symbol": "BTCUSDT",
        "open_time": _BASE,
        "open": Decimal("100"),
        "high": Decimal("111"),
        "low": Decimal("94"),
        "close": Decimal("105"),
        "volume": Decimal("1"),
    }
    base.update(overrides)
    return Kline(**base)


def test_same_candle_stop_and_take_profit_resolves_stop_first():
    folded = _folded()
    outcome = ProviderStatedPolicy().simulate(folded, [_bar()])

    assert outcome.folded_signal_id == folded.root_signal_id
    assert outcome.kind is SimOutcomeKind.R_MULTIPLE
    assert outcome.exit_reason == "stop"
    assert outcome.r_multiple == pytest.approx(-1.0)
    assert outcome.policy == "ProviderStatedPolicy"
    assert outcome.tie_break == "stop_first"


def test_market_entry_fills_at_next_kline_open_before_exit_checks():
    folded = _folded(
        timeline=[
            _step(
                effective_entry=None,
                leg_price=None,
                effective_stop_loss=Decimal("95"),
                effective_take_profits=[Decimal("110")],
            )
        ]
    )
    bar = _bar(
        open_time=_BASE + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal("111"),
        low=Decimal("98"),
    )

    outcome = ProviderStatedPolicy().simulate(folded, [bar])

    assert outcome.kind is SimOutcomeKind.R_MULTIPLE
    assert outcome.entry_fill_at == bar.open_time
    assert outcome.exit_reason == "tp"
    assert outcome.r_multiple == pytest.approx(2.0)
