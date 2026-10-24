from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from verasig.domain.lifecycle import FoldedSignal, FoldStep
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import Side, SignalEventType
from verasig.features.signals.patch import LifecyclePatch
from verasig.features.signals.views import _mod_kind, _mods

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


def test_a_reply_after_close_is_labelled_by_what_the_fold_applied():
    closed = _step().model_copy(
        update={"event_type": SignalEventType.CLOSE, "effective_size": Decimal(0)}
    )
    stop_move = _step().model_copy(
        update={"source_message_id": 3, "effective_size": Decimal(0)}
    )
    folded = FoldedSignal(
        root_signal_id=uuid4(),
        symbol="BTCUSDT",
        side=Side.LONG,
        timeline=[closed, stop_move],
    )
    reply = RawTelegramMessage(
        channel_id=1,
        message_id=3,
        text="close all, SL 90",
        posted_at=_AT,
        captured_at=_AT,
        has_media=False,
        raw_payload={},
    )

    [mod] = _mods(folded, {3: reply}, set())

    assert mod["kind"] == "move_stop"  # the close was not applied, the stop was
