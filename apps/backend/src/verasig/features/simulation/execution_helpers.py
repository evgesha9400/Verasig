"""Shared candle-replay helpers for the execution policies.

Replay is chronological: each bar sees only the lifecycle step in force when it
opened, so a later stop move, target revision or author close never reaches back
to an earlier candle. A signal the author closed before entry never fills; an
open position the author closed exits at the next bar's open.
"""

from collections.abc import Iterator
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


@dataclass(frozen=True)
class _BarExit:
    price: Decimal
    reason: str  # "stop" | "tp" | "close"


def _bars_with_steps(
    folded: FoldedSignal, bars: list[Kline]
) -> Iterator[tuple[Kline, FoldStep]]:
    """Pair each bar with the latest step posted at or before its open (the
    entry step until the first reply). The timeline is time-ordered, so one
    forward cursor serves the whole replay."""
    timeline = folded.timeline
    index = 0
    for bar in bars:
        while index + 1 < len(timeline) and timeline[index + 1].at <= bar.open_time:
            index += 1
        yield bar, timeline[index]


def _step_at_bar(folded: FoldedSignal, bar: Kline) -> FoldStep:
    return next(_bars_with_steps(folded, [bar]))[1]


def _author_closed(folded: FoldedSignal, bar: Kline) -> bool:
    return folded.closed_at is not None and bar.open_time >= folded.closed_at


def _stop_price(step: FoldStep) -> Decimal | None:
    return step.effective_stop_loss


def _stop_or_breakeven(step: FoldStep, entry: Decimal) -> Decimal:
    # The fold sets a breakeven stop to the effective entry, which a market entry
    # leaves unresolved (None); the simulated fill price is that breakeven.
    return entry if step.effective_stop_loss is None else step.effective_stop_loss


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


def _bar_exit(
    folded: FoldedSignal, bar: Kline, stop: Decimal, target: Decimal | None
) -> _BarExit | None:
    """How ``bar`` ends an open position, if it does; the stop wins a tie."""
    if _author_closed(folded, bar):
        return _BarExit(price=bar.open, reason="close")
    if _touches_stop(folded, bar, stop):
        return _BarExit(price=stop, reason="stop")
    if target is not None and _touches_target(folded, bar, target):
        return _BarExit(price=target, reason="tp")
    return None


def _exit_life_bars(bars: list[Kline], index: int, exit_: _BarExit) -> list[Kline]:
    # An author close fills at the bar's open, so that bar's range never counts.
    return bars[:index] if exit_.reason == "close" else bars[: index + 1]


def _r_multiple(
    side: Side, entry: Decimal, exit_price: Decimal, risk: Decimal
) -> Decimal:
    move = exit_price - entry if side is Side.LONG else entry - exit_price
    return move / risk


def _market_entry_fill(folded: FoldedSignal, klines: list[Kline]) -> _EntryFill | None:
    if not klines or _author_closed(folded, klines[0]):
        return None
    first_bar = klines[0]
    return _EntryFill(price=first_bar.open, at=first_bar.open_time, bars=klines)


def _limit_entry_fill(
    folded: FoldedSignal, entry: Decimal, klines: list[Kline]
) -> _EntryFill | None:
    for index, bar in enumerate(klines):
        if _author_closed(folded, bar):
            return None  # cancelled before the order filled
        if _touches_entry(folded, bar, entry):
            return _EntryFill(price=entry, at=bar.open_time, bars=klines[index:])
    return None


def _entry_fill(
    folded: FoldedSignal, step: FoldStep, klines: list[Kline]
) -> _EntryFill | None:
    if step.effective_entry is None:
        return _market_entry_fill(folded, klines)
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
