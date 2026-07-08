"""Verasig - Template Mining: structured field extraction.

Signals are line-structured, so each line is classified by the label it carries
(stop / target / entry / market) and its prices are routed to that field. A
header line that names the instrument or direction and carries a bare price is
read as the entry only when no labelled entry line claims it.

Faithful port of ``fields.js``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import regex as re

from .directions import DetectedEntity as DirectionEntity
from .directions import detect_directions
from .instruments import DetectedEntity as InstrumentEntity
from .instruments import detect_instruments
from .prices import DetectedPrice, detect_prices
from .text import NormalizedText, normalize_message_text

# JS `\b` is ASCII-only; re.ASCII mirrors that boundary semantics.
_A = re.IGNORECASE | re.ASCII

# "risk" is intentionally excluded: "Risk 2% / Risk 50 Reward 150" is position-
# sizing metadata, not a stop level, so it must not capture a stop value.
STOP_LABEL = re.compile(
    r"\b(sl|stop\s*loss|stoploss|stop|invalidation|invalid\b)\b", _A
)
TARGET_LABEL = re.compile(r"\b(tp\d*|take\s*profits?|targets?|tgt|partial)\b", _A)
ENTRY_LABEL = re.compile(
    r"\b(entry|entries|enter|buy\s*zone|sell\s*zone|zone|limit)\b", _A
)
ENTRY_AT = re.compile(r"@")
MARKET_LABEL = re.compile(
    r"\b(now|cmp|market|current\s*market\s*price|current\s*price)\b", _A
)
# Russian field labels (Cyrillic is not ASCII-\w, so these are substring tests).
STOP_LABEL_RU = re.compile(r"стоп", re.IGNORECASE)
TARGET_LABEL_RU = re.compile(
    r"цел|тейк|фикс[а-яё]*\s+прибыл[а-яё]*\s+на", re.IGNORECASE
)
ENTRY_LABEL_RU = re.compile(r"вход", re.IGNORECASE)
MARKET_RU = re.compile(r"по\s*рынк", re.IGNORECASE)
HAS_WORD = re.compile(r"[\p{L}]{2,}")


@dataclass
class SignalEntry:
    """A parsed entry level."""

    type: str  # "single" | "range" | "market" | "unknown"
    price: float | None = None
    min: float | None = None
    max: float | None = None
    raw: str | None = None


@dataclass
class StructuredFields:
    """The structured fields a message parses into (partial signal)."""

    instrument: str | None = None
    instrument_raw: str | None = None
    direction: str | None = None
    order_type: str | None = None
    entry: SignalEntry | None = None
    stop_loss: float | None = None
    take_profits: list[float] = field(default_factory=list)


@dataclass
class _State:
    entry: SignalEntry | None = None
    header_entry: SignalEntry | None = None
    market_marker: bool = False
    stop_loss: float | None = None
    take_profits: list[float] = field(default_factory=list)
    collecting: str | None = None


def _is_stop_line(line: str) -> bool:
    return bool(STOP_LABEL.search(line)) or bool(STOP_LABEL_RU.search(line))


def _is_target_line(line: str) -> bool:
    return bool(TARGET_LABEL.search(line)) or bool(TARGET_LABEL_RU.search(line))


def _is_entry_line(line: str) -> bool:
    return (
        bool(ENTRY_LABEL.search(line))
        or bool(ENTRY_AT.search(line))
        or bool(ENTRY_LABEL_RU.search(line))
    )


def _is_market_line(line: str) -> bool:
    return bool(MARKET_LABEL.search(line)) or bool(MARKET_RU.search(line))


def has_trading_label(text: str) -> bool:
    """True when the text carries any entry / stop / target field label."""
    return _is_stop_line(text) or _is_target_line(text) or _is_entry_line(text)


def _message_text(message) -> str:
    if isinstance(message, str):
        return message
    if message is None:
        return ""
    return getattr(message, "text", None) or (
        message.get("text", "") if isinstance(message, dict) else ""
    )


def _primary_instrument(
    clean: str, overlay: dict | None, instruments: list[InstrumentEntity] | None
) -> InstrumentEntity | None:
    entities = (
        instruments if instruments is not None else detect_instruments(clean, overlay)
    )
    return entities[0] if entities else None


def _primary_direction(
    clean: str, overlay: dict | None, directions: list[DirectionEntity] | None
) -> DirectionEntity | None:
    entities = (
        directions if directions is not None else detect_directions(clean, overlay)
    )
    if not entities:
        return None
    # A worded direction (high confidence) beats an ambiguous emoji; ties break
    # on position so the header direction wins.
    return sorted(entities, key=lambda e: (-e.confidence, e.start))[0]


def _entry_from_price(price: DetectedPrice | None) -> SignalEntry | None:
    if not price:
        return None
    if price.type == "range":
        return SignalEntry(type="range", min=price.min, max=price.max, raw=price.raw)
    return SignalEntry(type="single", price=price.value, raw=price.raw)


def _push_targets(targets: list[float], prices: list[DetectedPrice]) -> None:
    for price in prices:
        if price.type == "range":
            targets.append(price.min)
            targets.append(price.max)
        else:
            targets.append(price.value)


def _is_target_item_line(line: str, prices: list[DetectedPrice]) -> bool:
    # A bare target item under a "Targets/Цели" header: a price with no real words.
    return len(prices) > 0 and not HAS_WORD.search(line)


def _classify_line(line: str, state: _State, overlay: dict | None) -> None:
    prices = detect_prices(line)
    if _is_stop_line(line):
        state.collecting = None
        if state.stop_loss is None and prices:
            first = prices[0]
            state.stop_loss = first.value if first.value is not None else first.min
        return
    if _is_target_line(line):
        # A "Targets:" / "Цели:" header with no inline price opens collection mode.
        state.collecting = "targets"
        _push_targets(state.take_profits, prices)
        return
    if _is_entry_line(line):
        state.collecting = None
        if not state.entry and prices:
            state.entry = _entry_from_price(prices[0])
        elif not prices and _is_market_line(line):
            state.market_marker = True
        return
    if _is_market_line(line):
        state.collecting = None
        state.market_marker = True
        return
    # While collecting targets, append bare price lines and stop at the first
    # non-target line (e.g. boilerplate / promos).
    if state.collecting == "targets":
        if _is_target_item_line(line, prices):
            _push_targets(state.take_profits, prices)
            return
        state.collecting = None
    # Unlabelled line: a price next to the instrument/direction header is entry.
    is_header = (
        len(detect_instruments(line, overlay)) > 0
        or len(detect_directions(line, overlay)) > 0
    )
    if is_header and prices and not state.header_entry:
        state.header_entry = _entry_from_price(prices[0])


def _resolve_entry(state: _State) -> SignalEntry | None:
    if state.entry:
        return state.entry
    if state.market_marker:
        return None
    return state.header_entry or None


def _order_type_for(entry: SignalEntry | None) -> str:
    if not entry:
        return "market"
    if entry.type == "range":
        return "range"
    if entry.type == "single":
        return "limit"
    return "unknown"


def extract_signal_fields(
    message,
    overlay: dict | None = None,
    detections: dict | None = None,
) -> StructuredFields:
    detections = detections or {}
    normalized: NormalizedText = detections.get("normalized") or normalize_message_text(
        _message_text(message)
    )
    clean, lines = normalized.clean, normalized.lines
    instrument = _primary_instrument(clean, overlay, detections.get("instruments"))
    direction = _primary_direction(clean, overlay, detections.get("directions"))

    state = _State()
    for line in lines:
        _classify_line(line, state, overlay)

    entry = _resolve_entry(state)
    return StructuredFields(
        instrument=instrument.normalized if instrument else None,
        instrument_raw=instrument.raw if instrument else None,
        direction=direction.normalized if direction else None,
        order_type=_order_type_for(entry),
        entry=entry,
        stop_loss=state.stop_loss,
        take_profits=state.take_profits,
    )
