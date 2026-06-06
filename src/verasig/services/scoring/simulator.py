"""Pure simulation orchestration over folded signals and injected policies."""

from verasig.domain.lifecycle import FoldedSignal
from verasig.domain.simulation import Kline, SimOutcome
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
