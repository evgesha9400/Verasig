"""ExecutionPolicy implementations for conservative simulated outcomes."""

from decimal import Decimal

from verasig.domain.execution_ports import ExecutionPolicy
from verasig.domain.lifecycle import FoldedSignal
from verasig.domain.simulation import Kline, SimOutcome, SimOutcomeKind
from verasig.features.simulation.execution_helpers import (
    TIE_BREAK,
    _active_step,
    _entry_fill,
    _EntryFill,
    _first_take_profit,
    _mae,
    _mfe,
    _policy_name,
    _risk,
    _stop_price,
    _touches_stop,
    _touches_target,
    _unfilled,
)


class ProviderStatedPolicy(ExecutionPolicy):
    """Simulate using the provider-stated entry, stop, and first take-profit."""

    def simulate(self, folded: FoldedSignal, klines: list[Kline]) -> SimOutcome:
        step = _active_step(folded)
        fill = _entry_fill(folded, step, klines)
        stop = _stop_price(step)
        target = _first_take_profit(step)
        if fill is None or stop is None or target is None:
            return _unfilled(self, folded)
        risk = _risk(fill.price, stop)
        if risk == 0:
            # fill == stop leaves no risk unit; the R-multiple division would raise.
            return _unfilled(self, folded)
        for index, bar in enumerate(fill.bars):
            life_bars = fill.bars[: index + 1]
            touches_stop = _touches_stop(folded, bar, stop)
            touches_target = _touches_target(folded, bar, target)
            if touches_stop:
                return _r_outcome(
                    self, folded, fill, life_bars, risk, bar, "stop", Decimal(-1)
                )
            if touches_target:
                multiple = abs(target - fill.price) / risk
                return _r_outcome(
                    self, folded, fill, life_bars, risk, bar, "tp", multiple
                )
        return _unfilled(self, folded)


def _r_outcome(
    policy: object,
    folded: FoldedSignal,
    fill: _EntryFill,
    life_bars: list[Kline],
    risk: Decimal,
    bar: Kline,
    exit_reason: str,
    r_multiple: Decimal,
) -> SimOutcome:
    return SimOutcome(
        folded_signal_id=folded.root_signal_id,
        kind=SimOutcomeKind.R_MULTIPLE,
        r_multiple=float(r_multiple),
        mfe=_mfe(folded.side, fill.price, risk, life_bars),
        mae=_mae(folded.side, fill.price, risk, life_bars),
        entry_fill_at=fill.at,
        exit_at=bar.open_time,
        exit_reason=exit_reason,
        policy=_policy_name(policy),
        tie_break=TIE_BREAK,
    )
