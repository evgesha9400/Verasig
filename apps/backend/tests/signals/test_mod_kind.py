from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from verasig.domain.lifecycle import FoldStep
from verasig.domain.signal import Side, SignalEventType
from verasig.features.signals.patch import LifecyclePatch
from verasig.features.signals.views import _mod_kind

_AT = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)


def _step() -> FoldStep:
    return FoldStep(
        at=_AT,
        source_signal_id=uuid4(),
        source_message_id=2,
        event_type=SignalEventType.MODIFY,
        effective_stop_loss=Decimal("95"),
        effective_take_profits=[Decimal("110")],
        effective_size=Decimal(1),
        effective_entry=Decimal("100"),
        leg_size=None,
        leg_price=None,
    )


def test_take_profit_only_patch_is_move_target_not_move_stop():
    patch = LifecyclePatch(set_take_profits=[Decimal("120")])
    assert _mod_kind(Side.LONG, _step(), patch) == "move_target"


def test_stop_patch_is_move_stop():
    patch = LifecyclePatch(set_stop_loss=Decimal("99"))
    assert _mod_kind(Side.LONG, _step(), patch) == "move_stop"


def test_breakeven_patch_is_move_stop():
    patch = LifecyclePatch(stop_to_breakeven=True)
    assert _mod_kind(Side.LONG, _step(), patch) == "move_stop"
