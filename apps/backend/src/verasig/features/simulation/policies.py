"""ExecutionPolicy implementations for conservative simulated outcomes."""

from decimal import Decimal

from verasig.domain.execution_ports import ExecutionPolicy
from verasig.domain.lifecycle import FoldedSignal
from verasig.domain.simulation import Kline, SimOutcome, SimOutcomeKind
from verasig.features.simulation.execution_helpers import (
    TIE_BREAK,
    _bar_exit,
    _BarExit,
    _bars_with_steps,
    _entry_fill,
    _EntryFill,
    _exit_life_bars,
    _first_take_profit,
    _mae,
    _mfe,
    _policy_name,
    _r_multiple,
    _risk,
    _step_at_bar,
    _stop_or_breakeven,
    _stop_price,
    _unfilled,
)


class ProviderStatedPolicy(ExecutionPolicy):
    """Simulate using the provider-stated entry, stop, and first take-profit.

    The entry order is the original entry; once filled, each bar trades against
    the stop and first target in force when it opened. The risk unit is the
    stop in force at the fill.
    """

    def simulate(self, folded: FoldedSignal, klines: list[Kline]) -> SimOutcome:
        fill = _entry_fill(folded, folded.timeline[0], klines)
        if fill is None:
            return _unfilled(self, folded)
        fill_step = _step_at_bar(folded, fill.bars[0])
        risk_stop = _stop_price(fill_step)
        if risk_stop is None or _first_take_profit(fill_step) is None:
            return _unfilled(self, folded)
        risk = _risk(fill.price, risk_stop)
        if risk == 0:
            # fill == stop leaves no risk unit; the R-multiple division would raise.
            return _unfilled(self, folded)
        for index, (bar, step) in enumerate(_bars_with_steps(folded, fill.bars)):
            stop = _stop_or_breakeven(step, fill.price)
            exit_ = _bar_exit(folded, bar, stop, _first_take_profit(step))
            if exit_ is not None:
                life_bars = _exit_life_bars(fill.bars, index, exit_)
                return _r_outcome(self, folded, fill, life_bars, risk, bar, exit_)
        return _unfilled(self, folded)


def _r_outcome(
    policy: object,
    folded: FoldedSignal,
    fill: _EntryFill,
    life_bars: list[Kline],
    risk: Decimal,
    bar: Kline,
    exit_: _BarExit,
) -> SimOutcome:
    return SimOutcome(
        folded_signal_id=folded.root_signal_id,
        kind=SimOutcomeKind.R_MULTIPLE,
        r_multiple=float(_r_multiple(folded.side, fill.price, exit_.price, risk)),
        mfe=_mfe(folded.side, fill.price, risk, life_bars),
        mae=_mae(folded.side, fill.price, risk, life_bars),
        entry_fill_at=fill.at,
        exit_at=bar.open_time,
        exit_reason=exit_.reason,
        policy=_policy_name(policy),
        tie_break=TIE_BREAK,
    )
