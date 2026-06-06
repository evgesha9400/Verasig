"""Pure simulation orchestration over folded signals and injected policies."""

from datetime import datetime

from verasig.domain.lifecycle import FoldedSignal
from verasig.domain.simulation import Kline, SimOutcome
from verasig.foundation.market_data import MarketData
from verasig.services.scoring.policies import ExecutionPolicy, ProviderStatedPolicy


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


def _market_klines(
    folded: FoldedSignal,
    market_data: MarketData,
    end: datetime,
    interval: str,
) -> list[Kline]:
    return market_data.klines(folded.symbol, _simulation_start(folded), end, interval)


def simulate_outcomes_from_market_data(
    folded_signals: list[FoldedSignal],
    market_data: MarketData,
    end: datetime,
    interval: str = "1",
    policy: ExecutionPolicy = ProviderStatedPolicy(),
) -> list[SimOutcome]:
    """Fetch klines through the MarketData seam, then simulate each folded signal."""
    return [
        policy.simulate(folded, _market_klines(folded, market_data, end, interval))
        for folded in folded_signals
    ]
