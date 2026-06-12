from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from verasig.domain.lifecycle import FoldedSignal
from verasig.domain.protocols import ExecutionPolicy
from verasig.domain.risk_config import EntryMode, ExitSource, RiskConfig, Weighting
from verasig.domain.signal import Side
from verasig.domain.simulation import Kline, SimOutcome, SimOutcomeKind
from verasig.services.scoring.execution_helpers import (
    TIE_BREAK,
    _active_step,
    _mae,
    _mfe,
    _policy_name,
    _risk,
    _touches_entry,
    _touches_stop,
    _touches_target,
    _unfilled,
)


@dataclass(frozen=True)
class _WeightedFill:
    price: Decimal
    weight: Decimal


@dataclass(frozen=True)
class _RiskFill:
    price: Decimal
    at: datetime
    bars: list[Kline]


class RiskConfigPolicy(ExecutionPolicy):
    def __init__(self, config: RiskConfig) -> None:
        self._config = config

    def simulate(self, folded: FoldedSignal, klines: list[Kline]) -> SimOutcome:
        levels = self._entry_levels(folded)
        fill = self._filled_levels(folded, levels, klines)
        if fill is None:
            return _unfilled(self, folded)
        stop, target = self._exit_prices(folded, fill.price)
        return self._outcome(folded, fill, stop, target)

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

    def _filled_levels(
        self, folded: FoldedSignal, levels: list[Decimal], klines: list[Kline]
    ) -> _RiskFill | None:
        if not levels:
            return _market_fill(klines)
        fills: list[_WeightedFill] = []
        first_index = None
        filled_indexes: set[int] = set()
        for bar_index, bar in enumerate(klines):
            for level_index, level in enumerate(levels):
                if level_index in filled_indexes:
                    continue
                if not _touches_entry(folded, bar, level):
                    continue
                filled_indexes.add(level_index)
                fills.append(_WeightedFill(level, self._level_weight(level_index)))
                first_index = bar_index if first_index is None else first_index
        if first_index is None:
            return None
        return _RiskFill(
            price=self._average_entry(fills),
            at=klines[first_index].open_time,
            bars=klines[first_index:],
        )

    def _average_entry(self, fills: list[_WeightedFill]) -> Decimal:
        weight = sum((fill.weight for fill in fills), Decimal(0))
        return sum((fill.price * fill.weight for fill in fills), Decimal(0)) / weight

    def _exit_prices(
        self, folded: FoldedSignal, entry: Decimal
    ) -> tuple[Decimal | None, Decimal | None]:
        if self._config.exit_source is ExitSource.SIGNAL:
            step = _active_step(folded)
            target = (
                step.effective_take_profits[0] if step.effective_take_profits else None
            )
            return step.effective_stop_loss, target
        return _custom_exit_prices(folded.side, entry, self._config)

    def _outcome(
        self,
        folded: FoldedSignal,
        fill: _RiskFill,
        stop: Decimal | None,
        target: Decimal | None,
    ) -> SimOutcome:
        if stop is None or target is None:
            return _unfilled(self, folded)
        risk = _risk(fill.price, stop)
        if risk == 0:
            return _unfilled(self, folded)
        for index, bar in enumerate(fill.bars):
            life_bars = fill.bars[: index + 1]
            if _touches_stop(folded, bar, stop):
                return _r_outcome(
                    self, folded, fill, life_bars, risk, bar, stop, "stop", Decimal(-1)
                )
            if _touches_target(folded, bar, target):
                multiple = abs(target - fill.price) / risk
                return _r_outcome(
                    self, folded, fill, life_bars, risk, bar, target, "tp", multiple
                )
        return _unfilled(self, folded)

    def _level_weight(self, level_index: int) -> Decimal:
        if self._config.weighting is Weighting.MARTINGALE:
            return Decimal(2) ** level_index
        return Decimal(1)


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


def _market_fill(klines: list[Kline]) -> _RiskFill | None:
    if not klines:
        return None
    return _RiskFill(
        price=klines[0].open,
        at=klines[0].open_time,
        bars=klines,
    )


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
    fill: _RiskFill,
    life_bars: list[Kline],
    risk: Decimal,
    bar: Kline,
    exit_price: Decimal,
    exit_reason: str,
    r_multiple: Decimal,
) -> SimOutcome:
    return SimOutcome(
        folded_signal_id=folded.root_signal_id,
        kind=SimOutcomeKind.R_MULTIPLE,
        r_multiple=float(r_multiple),
        pct_return=_pct_return(folded.side, fill.price, exit_price, policy._config),
        mfe=_mfe(folded.side, fill.price, risk, life_bars),
        mae=_mae(folded.side, fill.price, risk, life_bars),
        entry_fill_at=fill.at,
        exit_at=bar.open_time,
        exit_reason=exit_reason,
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
