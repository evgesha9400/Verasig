"""RiskConfigPolicy: replay a folded signal under the user's risk model.

One chronological pass from the first fill: each bar first fills any ladder
level it touches (never after the position has exited or the author closed it),
then trades the running average entry against the exits in force when the bar
opened. A deeper level touched after the exit bar never alters the result.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from verasig.domain.execution_ports import ExecutionPolicy
from verasig.domain.lifecycle import FoldedSignal, FoldStep
from verasig.domain.risk_config import EntryMode, ExitSource, RiskConfig, Weighting
from verasig.domain.signal import Side
from verasig.domain.simulation import Kline, SimOutcome, SimOutcomeKind
from verasig.features.simulation.execution_helpers import (
    TIE_BREAK,
    _author_closed,
    _bar_exit,
    _BarExit,
    _bars_with_steps,
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
    _touches_entry,
    _unfilled,
)


@dataclass(frozen=True)
class _WeightedFill:
    price: Decimal
    weight: Decimal


class RiskConfigPolicy(ExecutionPolicy):
    def __init__(self, config: RiskConfig) -> None:
        self._config = config

    def simulate(self, folded: FoldedSignal, klines: list[Kline]) -> SimOutcome:
        levels = self._entry_levels(folded)
        start = _first_fill_index(folded, levels, klines)
        if start is None:
            return _unfilled(self, folded)
        bars = klines[start:]
        fill_step = _step_at_bar(folded, bars[0])
        if self._missing_signal_exits(fill_step):
            return _unfilled(self, folded)
        fills: dict[int, _WeightedFill] = {}
        for index, (bar, step) in enumerate(_bars_with_steps(folded, bars)):
            if not _author_closed(folded, bar):
                self._fill_touched_levels(folded, levels, bar, fills)
            entry = self._average_entry(fills.values()) if levels else bars[0].open
            stop, target, risk = self._exit_levels(folded, step, fill_step, entry)
            exit_ = _bar_exit(folded, bar, stop, target)
            if exit_ is None:
                continue
            if risk == 0:
                return _unfilled(self, folded)  # no risk unit to divide by
            fill = _EntryFill(price=entry, at=bars[0].open_time, bars=bars)
            life_bars = _exit_life_bars(bars, index, exit_)
            return _r_outcome(self, folded, fill, life_bars, risk, bar, exit_)
        return _unfilled(self, folded)

    def _entry_levels(self, folded: FoldedSignal) -> list[Decimal]:
        entry_range = _entry_range(folded)
        if entry_range is None:
            return []
        low, high = entry_range
        if self._config.entry_mode is EntryMode.FIRST:
            return [_near_edge(folded.side, low, high)]
        if self._config.entry_mode is EntryMode.MID:
            return [(low + high) / Decimal(2)]
        return _ladder_levels(folded.side, low, high, self._config.levels)

    def _fill_touched_levels(
        self,
        folded: FoldedSignal,
        levels: list[Decimal],
        bar: Kline,
        fills: dict[int, _WeightedFill],
    ) -> None:
        for level_index, level in enumerate(levels):
            if level_index not in fills and _touches_entry(folded, bar, level):
                fills[level_index] = _WeightedFill(
                    level, self._level_weight(level_index)
                )

    def _average_entry(self, fills: Iterable[_WeightedFill]) -> Decimal:
        fills = list(fills)
        weight = sum((fill.weight for fill in fills), Decimal(0))
        return sum((fill.price * fill.weight for fill in fills), Decimal(0)) / weight

    def _missing_signal_exits(self, step: FoldStep) -> bool:
        if self._config.exit_source is not ExitSource.SIGNAL:
            return False
        return _stop_price(step) is None or _first_take_profit(step) is None

    def _exit_levels(
        self,
        folded: FoldedSignal,
        step: FoldStep,
        fill_step: FoldStep,
        entry: Decimal,
    ) -> tuple[Decimal, Decimal | None, Decimal]:
        """(stop, target, risk unit) for a bar: the signal's levels in force at
        the bar (risk measured to the stop in force at the fill), or the custom
        percentages around the running average entry."""
        if self._config.exit_source is ExitSource.SIGNAL:
            stop = _stop_or_breakeven(step, entry)
            risk = _risk(entry, _stop_or_breakeven(fill_step, entry))
            return stop, _first_take_profit(step), risk
        stop, target = _custom_exit_prices(folded.side, entry, self._config)
        return stop, target, _risk(entry, stop)

    def _level_weight(self, level_index: int) -> Decimal:
        if self._config.weighting is Weighting.MARTINGALE:
            return Decimal(2) ** level_index
        return Decimal(1)


def _first_fill_index(
    folded: FoldedSignal, levels: list[Decimal], klines: list[Kline]
) -> int | None:
    """The first bar that fills an entry level (any bar, for a market entry),
    unless the author closed the signal first."""
    for index, bar in enumerate(klines):
        if _author_closed(folded, bar):
            return None
        if not levels or any(_touches_entry(folded, bar, level) for level in levels):
            return index
    return None


def _entry_range(folded: FoldedSignal) -> tuple[Decimal, Decimal] | None:
    step = folded.timeline[0]
    values = [
        value
        for value in (step.entry_low, step.entry_high, step.effective_entry)
        if value is not None
    ]
    if not values:
        return None
    return min(values), max(values)


def _near_edge(side: Side, low: Decimal, high: Decimal) -> Decimal:
    if side is Side.LONG:
        return high
    return low


def _ladder_levels(
    side: Side, low: Decimal, high: Decimal, levels: int
) -> list[Decimal]:
    if levels <= 1:
        return [_near_edge(side, low, high)]
    step = (high - low) / Decimal(levels - 1)
    if side is Side.LONG:
        return [high - step * index for index in range(levels)]
    return [low + step * index for index in range(levels)]


def _custom_exit_prices(
    side: Side, entry: Decimal, config: RiskConfig
) -> tuple[Decimal, Decimal]:
    stop_move = entry * config.stop_pct / Decimal(100)
    target_move = entry * config.tp_pct / Decimal(100)
    if side is Side.LONG:
        return entry - stop_move, entry + target_move
    return entry + stop_move, entry - target_move


def _r_outcome(
    policy: RiskConfigPolicy,
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
        pct_return=_pct_return(folded.side, fill.price, exit_.price, policy._config),
        mfe=_mfe(folded.side, fill.price, risk, life_bars),
        mae=_mae(folded.side, fill.price, risk, life_bars),
        entry_fill_at=fill.at,
        exit_at=bar.open_time,
        exit_reason=exit_.reason,
        policy=_policy_name(policy),
        tie_break=TIE_BREAK,
    )


def _pct_return(
    side: Side, entry: Decimal, exit_price: Decimal, config: RiskConfig
) -> float:
    if side is Side.LONG:
        price_return_pct = (exit_price - entry) / entry * Decimal(100)
    else:
        price_return_pct = (entry - exit_price) / entry * Decimal(100)
    sized_return = price_return_pct * Decimal(config.leverage) * config.risk_pct
    return float(sized_return / Decimal(100))
