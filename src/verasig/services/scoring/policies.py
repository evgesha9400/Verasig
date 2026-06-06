"""ExecutionPolicy implementations for conservative simulated outcomes."""

from decimal import Decimal
from typing import Protocol, runtime_checkable

from verasig.domain.lifecycle import FoldedSignal, FoldStep
from verasig.domain.signal import Side
from verasig.domain.simulation import Kline, SimOutcome, SimOutcomeKind

TIE_BREAK = "stop_first"


@runtime_checkable
class ExecutionPolicy(Protocol):
    def simulate(self, folded: FoldedSignal, klines: list[Kline]) -> SimOutcome: ...


def _policy_name(policy: object) -> str:
    return policy.__class__.__name__


def _active_step(folded: FoldedSignal) -> FoldStep:
    return folded.timeline[-1]


def _market_entry_price(klines: list[Kline]) -> Decimal | None:
    if not klines:
        return None
    return klines[0].open


def _simulation_entry_price(step: FoldStep, klines: list[Kline]) -> Decimal | None:
    if step.effective_entry is not None:
        return step.effective_entry
    return _market_entry_price(klines)


def _stop_price(step: FoldStep) -> Decimal | None:
    return step.effective_stop_loss


def _first_take_profit(step: FoldStep) -> Decimal | None:
    if not step.effective_take_profits:
        return None
    return step.effective_take_profits[0]


def _risk(entry: Decimal, stop: Decimal) -> Decimal:
    return abs(entry - stop)


def _long_touches_stop(bar: Kline, stop: Decimal) -> bool:
    return bar.low <= stop


def _long_touches_target(bar: Kline, target: Decimal) -> bool:
    return bar.high >= target


def _short_touches_stop(bar: Kline, stop: Decimal) -> bool:
    return bar.high >= stop


def _short_touches_target(bar: Kline, target: Decimal) -> bool:
    return bar.low <= target


def _touches_stop(folded: FoldedSignal, bar: Kline, stop: Decimal) -> bool:
    if folded.side is Side.LONG:
        return _long_touches_stop(bar, stop)
    return _short_touches_stop(bar, stop)


def _touches_target(folded: FoldedSignal, bar: Kline, target: Decimal) -> bool:
    if folded.side is Side.LONG:
        return _long_touches_target(bar, target)
    return _short_touches_target(bar, target)


def _favorable_move(side: Side, entry: Decimal, bar: Kline) -> Decimal:
    if side is Side.LONG:
        return bar.high - entry
    return entry - bar.low


def _adverse_move(side: Side, entry: Decimal, bar: Kline) -> Decimal:
    if side is Side.LONG:
        return entry - bar.low
    return bar.high - entry


def _max_positive(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal(0)
    return max(Decimal(0), *values)


def _mfe(side: Side, entry: Decimal, risk: Decimal, klines: list[Kline]) -> float:
    return float(
        _max_positive([_favorable_move(side, entry, bar) for bar in klines]) / risk
    )


def _mae(side: Side, entry: Decimal, risk: Decimal, klines: list[Kline]) -> float:
    return float(
        _max_positive([_adverse_move(side, entry, bar) for bar in klines]) / risk
    )


class ProviderStatedPolicy:
    """Simulate using the provider-stated entry, stop, and first take-profit."""

    def simulate(self, folded: FoldedSignal, klines: list[Kline]) -> SimOutcome:
        step = _active_step(folded)
        entry = _simulation_entry_price(step, klines)
        stop = _stop_price(step)
        target = _first_take_profit(step)
        if entry is None or stop is None or target is None:
            return _unfilled(self, folded)
        risk = _risk(entry, stop)
        for bar in klines:
            touches_stop = _touches_stop(folded, bar, stop)
            touches_target = _touches_target(folded, bar, target)
            if touches_stop:
                return _r_outcome(
                    self, folded, klines, entry, risk, bar, "stop", Decimal(-1)
                )
            if touches_target:
                multiple = abs(target - entry) / risk
                return _r_outcome(
                    self, folded, klines, entry, risk, bar, "tp", multiple
                )
        return _unfilled(self, folded)


def _unfilled(policy: object, folded: FoldedSignal) -> SimOutcome:
    return SimOutcome(
        folded_signal_id=folded.root_signal_id,
        kind=SimOutcomeKind.UNFILLED,
        mfe=0.0,
        mae=0.0,
        exit_reason="unfilled",
        policy=_policy_name(policy),
        tie_break=TIE_BREAK,
    )


def _r_outcome(
    policy: object,
    folded: FoldedSignal,
    klines: list[Kline],
    entry: Decimal,
    risk: Decimal,
    bar: Kline,
    exit_reason: str,
    r_multiple: Decimal,
) -> SimOutcome:
    return SimOutcome(
        folded_signal_id=folded.root_signal_id,
        kind=SimOutcomeKind.R_MULTIPLE,
        r_multiple=float(r_multiple),
        mfe=_mfe(folded.side, entry, risk, klines),
        mae=_mae(folded.side, entry, risk, klines),
        entry_fill_at=bar.open_time,
        exit_at=bar.open_time,
        exit_reason=exit_reason,
        policy=_policy_name(policy),
        tie_break=TIE_BREAK,
    )
