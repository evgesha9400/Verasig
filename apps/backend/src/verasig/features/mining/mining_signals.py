"""Miner Candidate -> domain (RawSignalEvent + ExtractedSignal).

The template miner already extracts the structured trade (instrument, direction,
entry, stop, targets) into a ``Candidate.fields``; this module is the single
translation site that maps one candidate onto the two rows the Signals view reads:
a ``RawSignalEvent`` (the candidate message) and an ``ExtractedSignal`` linked to
it. Direction ``BUY/SELL`` -> ``Side.LONG/SHORT``; entry ``single/range/market``
-> the matching ``EntryType``. Miner prices are floats; each is carried to a
``Decimal`` through ``str`` so the float's decimal form is preserved exactly.
"""

from decimal import Decimal

from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.signal import (
    EntryType,
    ExtractedSignal,
    ExtractionMethod,
    Side,
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


def _event_of(candidate: Candidate, channel_id: int) -> RawSignalEvent:
    return RawSignalEvent(
        channel_id=channel_id,
        message_id=int(candidate.message.id),
        candidate_text=candidate.message.text,
        materialized_by=MaterializationPath.MINING,
    )


def _signal_of(
    candidate: Candidate, event: RawSignalEvent, channel_id: int
) -> ExtractedSignal:
    fields = candidate.fields
    entry_low, entry_high = _entry_bounds(fields.entry)
    return ExtractedSignal(
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
        confidence=_to_decimal(candidate.confidence),
        event_id=event.id,
        channel_id=channel_id,
        event_type=SignalEventType.NEW_ENTRY,
        extraction_method=ExtractionMethod.DETERMINISTIC,
        rule_id=candidate.template_key,
    )


def candidate_to_event_and_signal(
    candidate: Candidate, channel_id: int
) -> tuple[RawSignalEvent, ExtractedSignal] | None:
    """One candidate -> (event, signal), or None when required fields are absent."""
    if not _is_persistable(candidate.fields):
        return None
    event = _event_of(candidate, channel_id)
    return event, _signal_of(candidate, event, channel_id)
