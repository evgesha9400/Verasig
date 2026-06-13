from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from verasig.domain.lifecycle import FoldedSignal, FoldStep
from verasig.domain.risk_config import EntryMode, ExitSource, RiskConfig, Weighting
from verasig.domain.signal import Side, SignalEventType
from verasig.domain.simulation import Kline, SimOutcomeKind
from verasig.features.risk.policy import RiskConfigPolicy

_BASE = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _config(**overrides) -> RiskConfig:
    values = {"exit_source": ExitSource.SIGNAL}
    values.update(overrides)
    return RiskConfig(**values)


def _folded(**overrides) -> FoldedSignal:
    base = {
        "root_signal_id": uuid4(),
        "symbol": "BTCUSDT",
        "side": Side.LONG,
        "timeline": [_step()],
    }
    base.update(overrides)
    return FoldedSignal(**base)


def _step(**overrides) -> FoldStep:
    base = {
        "at": _BASE,
        "source_signal_id": uuid4(),
        "source_message_id": 1,
        "event_type": SignalEventType.NEW_ENTRY,
        "effective_stop_loss": Decimal("95"),
        "effective_take_profits": [Decimal("115")],
        "effective_size": Decimal(1),
        "effective_entry": Decimal("100"),
        "entry_low": Decimal("100"),
        "entry_high": Decimal("110"),
        "leg_size": Decimal(1),
        "leg_price": Decimal("100"),
    }
    base.update(overrides)
    return FoldStep(**base)


def _bar(minutes: int = 0, **overrides) -> Kline:
    base = {
        "symbol": "BTCUSDT",
        "open_time": _BASE + timedelta(minutes=minutes),
        "open": Decimal("112"),
        "high": Decimal("112"),
        "low": Decimal("112"),
        "close": Decimal("112"),
        "volume": Decimal("1"),
    }
    base.update(overrides)
    return Kline(**base)


def test_first_entry_mode_fills_long_at_near_edge():
    outcome = RiskConfigPolicy(_config(entry_mode=EntryMode.FIRST)).simulate(
        _folded(),
        [
            _bar(low=Decimal("109"), high=Decimal("111")),
            _bar(1, low=Decimal("109"), high=Decimal("115")),
        ],
    )

    assert outcome.kind is SimOutcomeKind.R_MULTIPLE
    assert outcome.r_multiple == pytest.approx(1 / 3)


def test_mid_entry_mode_fills_when_midpoint_trades():
    outcome = RiskConfigPolicy(_config(entry_mode=EntryMode.MID)).simulate(
        _folded(),
        [
            _bar(low=Decimal("104"), high=Decimal("106")),
            _bar(1, low=Decimal("104"), high=Decimal("115")),
        ],
    )

    assert outcome.r_multiple == pytest.approx(1.0)


def test_equal_ladder_averages_only_touched_levels():
    outcome = RiskConfigPolicy(
        _config(entry_mode=EntryMode.LADDER, levels=3, weighting=Weighting.EQUAL)
    ).simulate(
        _folded(),
        [
            _bar(low=Decimal("104"), high=Decimal("106")),
            _bar(1, low=Decimal("104"), high=Decimal("115")),
        ],
    )

    assert outcome.r_multiple == pytest.approx(0.6)


def test_martingale_ladder_uses_weighted_average():
    outcome = RiskConfigPolicy(
        _config(entry_mode=EntryMode.LADDER, levels=3, weighting=Weighting.MARTINGALE)
    ).simulate(
        _folded(),
        [
            _bar(low=Decimal("99"), high=Decimal("106")),
            _bar(1, low=Decimal("99"), high=Decimal("115")),
        ],
    )

    assert outcome.r_multiple == pytest.approx(1.5454545)


def test_custom_exit_prices_use_risk_config_percentages_and_pct_return():
    outcome = RiskConfigPolicy(
        _config(
            entry_mode=EntryMode.MID,
            exit_source=ExitSource.CUSTOM,
            stop_pct=Decimal("2.5"),
            tp_pct=Decimal("7.5"),
            risk_pct=Decimal("2.0"),
            leverage=5,
        )
    ).simulate(
        _folded(
            timeline=[
                _step(
                    effective_stop_loss=None,
                    effective_take_profits=[],
                    effective_entry=Decimal("100"),
                    entry_low=Decimal("100"),
                    entry_high=Decimal("100"),
                )
            ]
        ),
        [
            _bar(low=Decimal("100"), high=Decimal("100")),
            _bar(1, low=Decimal("100"), high=Decimal("108")),
        ],
    )

    assert outcome.exit_reason == "tp"
    assert outcome.r_multiple == pytest.approx(3.0)
    assert outcome.pct_return == pytest.approx(0.75)


def test_no_touched_entry_level_is_unfilled():
    outcome = RiskConfigPolicy(_config(entry_mode=EntryMode.LADDER)).simulate(
        _folded(),
        [_bar(low=Decimal("111"), high=Decimal("120"))],
    )

    assert outcome.kind is SimOutcomeKind.UNFILLED
    assert outcome.pct_return is None


def test_same_candle_stop_and_target_resolves_stop_first_with_pct_return():
    outcome = RiskConfigPolicy(_config(entry_mode=EntryMode.MID)).simulate(
        _folded(
            timeline=[
                _step(
                    effective_stop_loss=Decimal("95"),
                    effective_take_profits=[Decimal("110")],
                    entry_low=Decimal("100"),
                    entry_high=Decimal("100"),
                )
            ]
        ),
        [
            _bar(low=Decimal("100"), high=Decimal("100")),
            _bar(1, low=Decimal("94"), high=Decimal("111")),
        ],
    )

    assert outcome.exit_reason == "stop"
    assert outcome.r_multiple == pytest.approx(-1.0)
    assert outcome.pct_return == pytest.approx(-0.5)
