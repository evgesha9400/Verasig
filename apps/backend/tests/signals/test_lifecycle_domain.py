from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from verasig.domain.lifecycle import (
    FOLD_VERSION,
    FoldedSignal,
    FoldStep,
)
from verasig.domain.signal import Side, SignalEventType


def _instant() -> datetime:
    return datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)


def _step(**overrides) -> FoldStep:
    base = {
        "at": _instant(),
        "source_signal_id": uuid4(),
        "source_message_id": 1,
        "event_type": SignalEventType.NEW_ENTRY,
        "effective_size": Decimal(1),
    }
    base.update(overrides)
    return FoldStep(**base)


def test_fold_version_constant_is_one():
    assert FOLD_VERSION == 1


def test_fold_step_defaults_effective_optionals_to_empty_or_none():
    step = _step()
    assert step.effective_take_profits == []
    assert step.effective_stop_loss is None
    assert step.effective_entry is None
    assert step.leg_size is None
    assert step.leg_price is None


def test_fold_step_records_effective_state_after_step():
    step = _step(
        event_type=SignalEventType.MODIFY,
        effective_stop_loss=Decimal("65000"),
        effective_take_profits=[Decimal("67000"), Decimal("68000")],
        effective_size=Decimal(2),
        effective_entry=Decimal("64000"),
        leg_size=Decimal(1),
        leg_price=Decimal("63000"),
    )
    assert step.event_type is SignalEventType.MODIFY
    assert step.effective_take_profits == [Decimal("67000"), Decimal("68000")]
    assert step.effective_size == Decimal(2)


def test_folded_signal_defaults_closed_at_none_and_stamps_fold_version():
    folded = FoldedSignal(
        root_signal_id=uuid4(),
        symbol="BTCUSDT",
        side=Side.LONG,
        timeline=[_step()],
    )
    assert folded.closed_at is None
    assert folded.fold_version == FOLD_VERSION
    assert len(folded.timeline) == 1
