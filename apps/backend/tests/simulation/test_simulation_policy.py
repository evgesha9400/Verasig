from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from verasig.domain.lifecycle import FoldedSignal, FoldStep
from verasig.domain.signal import Side, SignalEventType
from verasig.domain.simulation import Kline, SimOutcomeKind
from verasig.features.simulation.policies import ProviderStatedPolicy

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


def test_zero_risk_when_stop_equals_entry_returns_unfilled_without_dividing():
    # stop == entry leaves no risk unit; the R-multiple division must not blow up.
    folded = _folded(
        timeline=[_step(effective_stop_loss=Decimal("100"), leg_price=Decimal("100"))]
    )

    outcome = ProviderStatedPolicy().simulate(folded, [_bar()])

    assert outcome.kind is SimOutcomeKind.UNFILLED
    assert outcome.r_multiple is None


def test_limit_entry_stays_unfilled_when_price_never_reaches_entry():
    folded = _folded()
    bars = [
        _bar(high=Decimal("112"), low=Decimal("101")),
        _bar(
            open_time=_BASE + timedelta(minutes=1),
            high=Decimal("115"),
            low=Decimal("102"),
        ),
    ]

    outcome = ProviderStatedPolicy().simulate(folded, bars)

    assert outcome.kind is SimOutcomeKind.UNFILLED
    assert outcome.entry_fill_at is None
    assert outcome.exit_at is None
    assert outcome.exit_reason == "unfilled"
    assert outcome.r_multiple is None


def test_mfe_and_mae_stop_at_the_exit_candle():
    folded = _folded()
    bars = [
        _bar(high=Decimal("104"), low=Decimal("99")),
        _bar(
            open_time=_BASE + timedelta(minutes=1),
            high=Decimal("110"),
            low=Decimal("97"),
        ),
        _bar(
            open_time=_BASE + timedelta(minutes=2),
            high=Decimal("130"),
            low=Decimal("90"),
        ),
    ]

    outcome = ProviderStatedPolicy().simulate(folded, bars)

    assert outcome.exit_reason == "tp"
    assert outcome.r_multiple == pytest.approx(2.0)
    assert outcome.mfe == pytest.approx(2.0)
    assert outcome.mae == pytest.approx(0.6)


# --- chronological replay: a reply only acts on bars that open after it -------
def _minute(minutes: int) -> datetime:
    return _BASE + timedelta(minutes=minutes)


def _modify(minutes: int, **overrides) -> FoldStep:
    values = {
        "at": _minute(minutes),
        "source_message_id": 2,
        "event_type": SignalEventType.MODIFY,
        "leg_size": None,
        "leg_price": None,
    }
    values.update(overrides)
    return _step(**values)


def _close(minutes: int) -> FoldStep:
    return _modify(minutes, event_type=SignalEventType.CLOSE, effective_size=Decimal(0))


def _filling_bar() -> Kline:
    return _bar(open=Decimal("101"), high=Decimal("101"), low=Decimal("99.5"))


def test_a_later_stop_move_does_not_reach_back_to_earlier_candles():
    folded = _folded(timeline=[_step(), _modify(3, effective_stop_loss=Decimal("99"))])
    bars = [
        _filling_bar(),
        _bar(open_time=_minute(1), high=Decimal("104"), low=Decimal("98")),
        _bar(open_time=_minute(3), high=Decimal("111"), low=Decimal("99.5")),
    ]

    outcome = ProviderStatedPolicy().simulate(folded, bars)

    # the 98 low precedes the move to 99, so only the original 95 stop applied
    assert outcome.exit_reason == "tp"
    assert outcome.r_multiple == pytest.approx(2.0)


def test_breakeven_move_keeps_the_original_risk_unit():
    folded = _folded(timeline=[_step(), _modify(2, effective_stop_loss=Decimal("100"))])
    bars = [
        _filling_bar(),
        _bar(open_time=_minute(1), high=Decimal("105"), low=Decimal("100.5")),
        _bar(open_time=_minute(2), high=Decimal("104"), low=Decimal("99.9")),
    ]

    outcome = ProviderStatedPolicy().simulate(folded, bars)

    assert outcome.kind is SimOutcomeKind.R_MULTIPLE
    assert outcome.exit_reason == "stop"
    assert outcome.r_multiple == pytest.approx(0.0)
    assert outcome.exit_at == _minute(2)


def test_author_close_after_fill_exits_at_the_next_bar_open():
    folded = _folded(timeline=[_step(), _close(2)], closed_at=_minute(2))
    bars = [
        _filling_bar(),
        _bar(open_time=_minute(1), high=Decimal("104"), low=Decimal("99")),
        _bar(open_time=_minute(2), open=Decimal("103"), high=Decimal("130")),
    ]

    outcome = ProviderStatedPolicy().simulate(folded, bars)

    assert outcome.exit_reason == "close"
    assert outcome.r_multiple == pytest.approx(0.6)
    assert outcome.exit_at == _minute(2)
    assert outcome.mfe == pytest.approx(0.8)  # the close bar's range never counts


def test_target_hit_before_the_author_close_is_kept():
    folded = _folded(timeline=[_step(), _close(3)], closed_at=_minute(3))
    bars = [
        _filling_bar(),
        _bar(open_time=_minute(1), high=Decimal("111"), low=Decimal("100")),
    ]

    outcome = ProviderStatedPolicy().simulate(folded, bars)

    assert outcome.exit_reason == "tp"
    assert outcome.r_multiple == pytest.approx(2.0)


def test_signal_cancelled_before_entry_never_fills():
    folded = _folded(timeline=[_step(), _close(1)], closed_at=_minute(1))
    bars = [
        _bar(high=Decimal("105"), low=Decimal("101")),
        _bar(open_time=_minute(1), high=Decimal("111"), low=Decimal("94")),
    ]

    outcome = ProviderStatedPolicy().simulate(folded, bars)

    assert outcome.kind is SimOutcomeKind.UNFILLED
