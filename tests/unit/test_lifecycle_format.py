from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from verasig.cli import format_folded
from verasig.domain.lifecycle import FoldedSignal, FoldStep
from verasig.domain.signal import Side, SignalEventType

_ROOT = UUID("3f2a0000-0000-0000-0000-000000000000")


def _at(hour: int, minute: int) -> datetime:
    return datetime(2026, 6, 4, hour, minute, tzinfo=timezone.utc)


def _folded() -> FoldedSignal:
    return FoldedSignal(
        root_signal_id=_ROOT,
        symbol="BTCUSDT",
        side=Side.LONG,
        closed_at=_at(13, 10),
        timeline=[
            FoldStep(
                at=_at(12, 0),
                source_signal_id=_ROOT,
                source_message_id=1,
                event_type=SignalEventType.NEW_ENTRY,
                effective_stop_loss=Decimal("64000"),
                effective_take_profits=[Decimal("67000")],
                effective_size=Decimal(1),
                effective_entry=Decimal("65000"),
                leg_size=Decimal(1),
                leg_price=Decimal("65000"),
            ),
            FoldStep(
                at=_at(12, 30),
                source_signal_id=_ROOT,
                source_message_id=2,
                event_type=SignalEventType.MODIFY,
                effective_stop_loss=Decimal("64000"),
                effective_take_profits=[Decimal("67000")],
                effective_size=Decimal(2),
                effective_entry=Decimal("64000"),
                leg_size=Decimal(1),
                leg_price=Decimal("63000"),
            ),
            FoldStep(
                at=_at(13, 10),
                source_signal_id=_ROOT,
                source_message_id=3,
                event_type=SignalEventType.CLOSE,
                effective_size=Decimal(0),
                leg_size=Decimal(-2),
            ),
        ],
    )


def test_header_carries_symbol_side_root_prefix_steps_and_closed():
    header = format_folded(_folded()).splitlines()[0]
    assert "BTCUSDT LONG" in header
    assert "root=3f2a0000" in header
    assert "steps=3" in header
    assert "closed=2026-06-04T13:10Z" in header


def test_entry_row_shows_effective_levels():
    entry_row = format_folded(_folded()).splitlines()[1]
    assert "NEW_ENTRY" in entry_row
    assert "sl=64000" in entry_row
    assert "tps=[67000]" in entry_row  # no quotes around the numbers
    assert "size=1" in entry_row
    assert "entry=65000" in entry_row


def test_add_row_is_annotated_and_carries_weighted_entry():
    add_row = format_folded(_folded()).splitlines()[2]
    assert "MODIFY" in add_row
    assert "size=2" in add_row
    assert "entry=64000" in add_row
    assert "(add)" in add_row


def test_close_row_shows_zero_size():
    close_row = format_folded(_folded()).splitlines()[3]
    assert "CLOSE" in close_row
    assert "size=0" in close_row


def test_open_lifecycle_renders_dash_for_not_closed():
    folded = _folded()
    folded.closed_at = None
    assert "closed=-" in format_folded(folded).splitlines()[0]
