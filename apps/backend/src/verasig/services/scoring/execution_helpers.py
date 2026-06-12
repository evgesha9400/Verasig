from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from verasig.domain.lifecycle import FoldedSignal, FoldStep
from verasig.domain.signal import Side
from verasig.domain.simulation import Kline, SimOutcome, SimOutcomeKind

TIE_BREAK = "stop_first"


@dataclass(frozen=True)
class _EntryFill:
    price: Decimal
    at: datetime
    bars: list[Kline]


def _policy_name(policy: object) -> str:
    return policy.__class__.__name__


def _active_step(folded: FoldedSignal) -> FoldStep:
    return folded.timeline[-1]


def _stop_price(step: FoldStep) -> Decimal | None:
    return step.effective_stop_loss


def _first_take_profit(step: FoldStep) -> Decimal | None:
    if not step.effective_take_profits:
        return None
    return step.effective_take_profits[0]


def _risk(entry: Decimal, stop: Decimal) -> Decimal:
    return abs(entry - stop)


def _touches_stop(folded: FoldedSignal, bar: Kline, stop: Decimal) -> bool:
    if folded.side is Side.LONG:
        return bar.low <= stop
    return bar.high >= stop


def _touches_target(folded: FoldedSignal, bar: Kline, target: Decimal) -> bool:
    if folded.side is Side.LONG:
        return bar.high >= target
    return bar.low <= target


def _touches_entry(folded: FoldedSignal, bar: Kline, entry: Decimal) -> bool:
    if folded.side is Side.LONG:
        return bar.low <= entry
    return bar.high >= entry


def _market_entry_fill(klines: list[Kline]) -> _EntryFill | None:
    if not klines:
        return None
    first_bar = klines[0]
    return _EntryFill(price=first_bar.open, at=first_bar.open_time, bars=klines)


def _limit_entry_fill(
    folded: FoldedSignal, entry: Decimal, klines: list[Kline]
) -> _EntryFill | None:
    for index, bar in enumerate(klines):
        if _touches_entry(folded, bar, entry):
            return _EntryFill(price=entry, at=bar.open_time, bars=klines[index:])
    return None


def _entry_fill(
    folded: FoldedSignal, step: FoldStep, klines: list[Kline]
) -> _EntryFill | None:
    if step.effective_entry is None:
        return _market_entry_fill(klines)
    return _limit_entry_fill(folded, step.effective_entry, klines)


def _mfe(side: Side, entry: Decimal, risk: Decimal, klines: list[Kline]) -> float:
    return float(
        _max_positive([_favorable_move(side, entry, bar) for bar in klines]) / risk
    )


def _mae(side: Side, entry: Decimal, risk: Decimal, klines: list[Kline]) -> float:
    return float(
        _max_positive([_adverse_move(side, entry, bar) for bar in klines]) / risk
    )


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
