"""Miner Candidate -> domain (Signal).

The template miner already extracts the structured trade (instrument, direction,
entry, stop, targets) into a ``Candidate.fields``; this module is the single
translation site that maps one candidate onto the ``Signal`` the Signals view
reads. Direction ``BUY/SELL`` -> ``Side.LONG/SHORT``; entry ``single/range/market``
-> the matching ``EntryType``; the stated leverage (the max of a range) carries
over. Miner prices are floats; each is carried to a
``Decimal`` through ``str`` so the float's decimal form is preserved exactly.
"""

from decimal import Decimal

from verasig.domain.signal import (
    EntryType,
    Side,
    Signal,
    SignalEventType,
)
from verasig.features.mining.template_mining.fields import SignalEntry, StructuredFields
from verasig.features.mining.template_mining.types import Candidate

_SIDE_BY_DIRECTION = {"BUY": Side.LONG, "SELL": Side.SHORT}
_ENTRY_TYPE_BY_KIND = {
    "single": EntryType.LIMIT_SINGLE,
    "range": EntryType.LIMIT_RANGE,
    "market": EntryType.MARKET,
}


def _to_decimal(value: float | None) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _entry_bounds(entry: SignalEntry | None) -> tuple[Decimal | None, Decimal | None]:
    if entry is None or entry.type == "market":
        return None, None
    if entry.type == "range":
        return _to_decimal(entry.min), _to_decimal(entry.max)
    price = _to_decimal(entry.price)
    return price, price


def _entry_type_of(entry: SignalEntry | None) -> EntryType:
    if entry is None:
        return EntryType.MARKET
    return _ENTRY_TYPE_BY_KIND.get(entry.type, EntryType.MARKET)


def _is_persistable(fields: StructuredFields) -> bool:
    """A candidate persists only when both required trade fields are present."""
    return bool(fields.instrument) and fields.direction in _SIDE_BY_DIRECTION


def _signal_of(candidate: Candidate, channel_id: int, rule_id: str) -> Signal:
    fields = candidate.fields
    entry_low, entry_high = _entry_bounds(fields.entry)
    return Signal(
        symbol=fields.instrument,
        side=_SIDE_BY_DIRECTION[fields.direction],
        entry_type=_entry_type_of(fields.entry),
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=_to_decimal(fields.stop_loss),
        take_profits=[
            price
            for value in fields.take_profits
            if (price := _to_decimal(value)) is not None
        ],
        leverage=_to_decimal(fields.leverage),
        confidence=_to_decimal(candidate.confidence),
        channel_id=channel_id,
        message_id=int(candidate.message.id),
        candidate_text=candidate.message.text,
        event_type=SignalEventType.NEW_ENTRY,
        rule_id=rule_id,
    )


def candidate_to_signal(
    candidate: Candidate, channel_id: int, rule_id: str
) -> Signal | None:
    """One candidate -> a Signal, or None when required trade fields are absent.

    ``rule_id`` is the claiming accepted family's ``template_key`` - the
    candidate's own key on an exact match, the general family's on a fallback -
    so a reopened feed reseeds exactly the families that produced its signals."""
    if not _is_persistable(candidate.fields):
        return None
    return _signal_of(candidate, channel_id, rule_id)
