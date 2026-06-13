"""Pure execution simulation seams."""

from typing import Protocol, runtime_checkable

from verasig.domain.lifecycle import FoldedSignal
from verasig.domain.simulation import Kline, SimOutcome


@runtime_checkable
class ExecutionPolicy(Protocol):
    def simulate(self, folded: FoldedSignal, klines: list[Kline]) -> SimOutcome: ...
