from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from verasig.domain.lifecycle import FoldedSignal, FoldStep
from verasig.domain.signal import Side, SignalEventType
from verasig.domain.simulation import Kline, SimOutcome, SimOutcomeKind
from verasig.features.simulation.simulator import simulate_outcomes

_BASE = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


class CustomRiskPolicy:
    @staticmethod
    def simulate(folded: FoldedSignal, klines: list[Kline]) -> SimOutcome:
        return SimOutcome(
            folded_signal_id=folded.root_signal_id,
            kind=SimOutcomeKind.UNFILLED,
            mfe=float(len(klines)),
            mae=0.0,
            exit_reason="custom",
            policy="CustomRiskPolicy",
            tie_break="custom",
        )


def _folded() -> FoldedSignal:
    return FoldedSignal(
        root_signal_id=uuid4(),
        symbol="BTCUSDT",
        side=Side.LONG,
        timeline=[
            FoldStep(
                at=_BASE,
                source_signal_id=uuid4(),
                source_message_id=1,
                event_type=SignalEventType.NEW_ENTRY,
                effective_size=Decimal(1),
            )
        ],
    )


def _bar(symbol: str) -> Kline:
    return Kline(
        symbol=symbol,
        open_time=_BASE,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("1"),
    )


def test_simulator_uses_injected_policy_for_each_folded_signal():
    folded = _folded()

    outcomes = simulate_outcomes(
        folded_signals=[folded],
        klines_by_symbol={"BTCUSDT": [_bar("BTCUSDT")]},
        policy=CustomRiskPolicy(),
    )

    assert len(outcomes) == 1
    assert outcomes[0].folded_signal_id == folded.root_signal_id
    assert outcomes[0].policy == "CustomRiskPolicy"
    assert outcomes[0].exit_reason == "custom"
    assert outcomes[0].mfe == 1.0
