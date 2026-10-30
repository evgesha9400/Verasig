"""Pure simulation orchestration over folded signals and injected policies."""

from bisect import bisect_left
from datetime import datetime

from verasig.domain.execution_ports import ExecutionPolicy
from verasig.domain.lifecycle import FoldedSignal
from verasig.domain.market_ports import MarketData
from verasig.domain.simulation import Kline, SimOutcome
from verasig.features.simulation.policies import ProviderStatedPolicy


def _klines_for_symbol(
    folded: FoldedSignal,
    klines_by_symbol: dict[str, list[Kline]],
) -> list[Kline]:
    return klines_by_symbol.get(folded.symbol, [])


def simulate_outcomes(
    folded_signals: list[FoldedSignal],
    klines_by_symbol: dict[str, list[Kline]],
    policy: ExecutionPolicy = ProviderStatedPolicy(),
) -> list[SimOutcome]:
    """Simulate each folded signal with the injected execution policy."""
    return [
        policy.simulate(folded, _klines_for_symbol(folded, klines_by_symbol))
        for folded in folded_signals
    ]


def _simulation_start(folded: FoldedSignal) -> datetime:
    return folded.timeline[0].at


def _klines_by_symbol(
    folded_signals: list[FoldedSignal],
    market_data: MarketData,
    end: datetime,
    interval: str,
) -> dict[str, list[Kline]]:
    """One fetch per symbol, from its earliest signal to ``end``."""
    starts: dict[str, datetime] = {}
    for folded in folded_signals:
        start = _simulation_start(folded)
        starts[folded.symbol] = min(start, starts.get(folded.symbol, start))
    return {
        symbol: market_data.klines(symbol, start, end, interval)
        for symbol, start in starts.items()
    }


def _klines_from(klines: list[Kline], start: datetime) -> list[Kline]:
    # A signal sees only the bars a fetch starting at its own entry would return.
    return klines[bisect_left(klines, start, key=lambda kline: kline.open_time) :]


def simulate_outcomes_from_market_data(
    folded_signals: list[FoldedSignal],
    market_data: MarketData,
    end: datetime,
    interval: str = "1",
    policy: ExecutionPolicy = ProviderStatedPolicy(),
) -> list[SimOutcome]:
    """Fetch klines through the MarketData seam, then simulate each folded signal.
    Signals on one symbol share a single fetch."""
    klines_by_symbol = _klines_by_symbol(folded_signals, market_data, end, interval)
    return [
        policy.simulate(
            folded,
            _klines_from(klines_by_symbol[folded.symbol], _simulation_start(folded)),
        )
        for folded in folded_signals
    ]
