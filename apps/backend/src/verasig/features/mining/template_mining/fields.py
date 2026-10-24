"""Verasig - Template Mining: structured field extraction.

Signals are line-structured, and a line may carry several labelled clauses
("BTC LONG entry 100 sl 95 tp 110"). Each line is partitioned at its field
labels (stop / target / entry / market) and the prices inside each clause are
routed to that field. A price ahead of the first label on a header line (one
naming the instrument or direction) is read as the entry only when no labelled
entry claims it.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field, replace

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
# "@" marks an entry only when a price follows it ("@ 2320"), not "@admin".
ENTRY_AT = re.compile(r"@(?=\s*\d)")
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
# Leverage: a single multiplier ("20x", Cyrillic "20х") or a range ("5-10x"),
# glued to its "x" as the price detector requires. Shared with the template
# normalizer, which collapses it to <LEVERAGE>.
_LEVERAGE_VALUE = r"[0-9]+(?:\.[0-9]+)?"
LEVERAGE = re.compile(
    rf"({_LEVERAGE_VALUE})(?:\s*-\s*({_LEVERAGE_VALUE}))?[xXхХ](?![\p{{L}}0-9])"
)


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
    leverage: float | None = None


@dataclass
class _State:
    entry: SignalEntry | None = None
    header_entry: SignalEntry | None = None
    market_marker: bool = False
    stop_loss: float | None = None
    take_profits: list[float] = field(default_factory=list)
    collecting: str | None = None


@dataclass
class _Label:
    kind: str  # "stop" | "target" | "entry" | "market"
    start: int
    end: int


_LABEL_MATCHERS = (
    ("stop", STOP_LABEL),
    ("stop", STOP_LABEL_RU),
    ("target", TARGET_LABEL),
    ("target", TARGET_LABEL_RU),
    ("entry", ENTRY_LABEL),
    ("entry", ENTRY_AT),
    ("entry", ENTRY_LABEL_RU),
    ("market", MARKET_LABEL),
    ("market", MARKET_RU),
)
_FIELD_KINDS = {"stop", "target", "entry"}


def _labels_of(line: str) -> list[_Label]:
    """The line's field labels in source order, overlaps dropped."""
    found = sorted(
        (
            _Label(kind, match.start(), match.end())
            for kind, matcher in _LABEL_MATCHERS
            for match in matcher.finditer(line)
        ),
        key=lambda label: (label.start, -label.end),
    )
    labels: list[_Label] = []
    cursor = -1
    for label in found:
        if label.start < cursor:
            continue
        labels.append(label)
        cursor = label.end
    return labels


def has_trading_label(text: str) -> bool:
    """True when the text carries any entry / stop / target field label."""
    return any(label.kind in _FIELD_KINDS for label in _labels_of(text))


def _message_text(message) -> str:
    if isinstance(message, str):
        return message
    if message is None:
        return ""
    return getattr(message, "text", None) or (
        message.get("text", "") if isinstance(message, dict) else ""
    )


def _line_of(clean: str, index: int) -> int:
    return clean.count("\n", 0, index)


def _primary_instrument(
    clean: str,
    overlay: dict | None,
    instruments: list[InstrumentEntity] | None,
    direction: DirectionEntity | None,
) -> InstrumentEntity | None:
    entities = (
        instruments if instruments is not None else detect_instruments(clean, overlay)
    )
    if not entities:
        return None
    # The instrument on the primary direction's line is the traded one; ties
    # break on confidence, then position. Detection keeps one entity per symbol
    # (its first mention), so "ETH and BTC watchlist\nBTC LONG" matches the
    # direction line by symbol, not only by the kept entity's position.
    direction_line = _line_of(clean, direction.start) if direction else None
    on_direction_line = _symbols_on_direction_line(clean, overlay, direction_line)
    return sorted(
        entities,
        key=lambda e: (
            _line_of(clean, e.start) != direction_line
            and e.normalized not in on_direction_line,
            -e.confidence,
            e.start,
        ),
    )[0]


def _symbols_on_direction_line(
    clean: str, overlay: dict | None, direction_line: int | None
) -> set[str]:
    if direction_line is None:
        return set()
    line = clean.split("\n")[direction_line]
    return {entity.normalized for entity in detect_instruments(line, overlay)}


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


def _is_header_line(line: str, overlay: dict | None) -> bool:
    return (
        len(detect_instruments(line, overlay)) > 0
        or len(detect_directions(line, overlay)) > 0
    )


def _route_clause(
    kind: str, prices: list[DetectedPrice], has_market: bool, state: _State
) -> None:
    if kind == "stop":
        if state.stop_loss is None and prices:
            first = prices[0]
            state.stop_loss = first.value if first.value is not None else first.min
    elif kind == "target":
        _push_targets(state.take_profits, prices)
    elif kind == "entry" and prices:
        if not state.entry:
            state.entry = _entry_from_price(prices[0])
    elif kind == "market" or has_market:
        state.market_marker = True  # "Buy now" / "Entry: CMP" with no price


def _classify_unlabelled_line(
    line: str, prices: list[DetectedPrice], state: _State, overlay: dict | None
) -> None:
    # While collecting targets, append bare price lines and stop at the first
    # non-target line (e.g. boilerplate / promos).
    if state.collecting == "targets":
        if _is_target_item_line(line, prices):
            _push_targets(state.take_profits, prices)
            return
        state.collecting = None
    # A price next to the instrument/direction header is the entry.
    if prices and not state.header_entry and _is_header_line(line, overlay):
        state.header_entry = _entry_from_price(prices[0])


@dataclass
class _Clause:
    kind: str
    start: int
    end: int
    has_market: bool = False


def _clauses_of(labels: list[_Label], line_end: int) -> list[_Clause]:
    """Partition a line at its field labels. A market label after another label
    qualifies that clause ("Entry now 64000") instead of opening its own."""
    clauses: list[_Clause] = []
    for label in labels:
        if label.kind == "market" and clauses:
            clauses[-1].has_market = True
            continue
        if clauses:
            clauses[-1].end = label.start
        clauses.append(_Clause(label.kind, label.start, line_end))
    return clauses


def _classify_line(
    line: str, prices: list[DetectedPrice], state: _State, overlay: dict | None
) -> None:
    labels = _labels_of(line)
    if not labels:
        _classify_unlabelled_line(line, prices, state, overlay)
        return
    clauses = _clauses_of(labels, len(line))
    leading = [price for price in prices if price.start < clauses[0].start]
    # A price ahead of the first label is the header's entry on a header line;
    # elsewhere it belongs to the first clause ("95 SL").
    if leading and _is_header_line(line, overlay):
        if not state.header_entry:
            state.header_entry = _entry_from_price(leading[0])
    else:
        clauses[0].start = 0
    for clause in clauses:
        clause_prices = [p for p in prices if clause.start <= p.start < clause.end]
        _route_clause(clause.kind, clause_prices, clause.has_market, state)
    # A trailing target label ("Targets:") keeps collecting bare price lines.
    state.collecting = "targets" if clauses[-1].kind == "target" else None


def _prices_by_line(
    lines: list[str], prices: list[DetectedPrice]
) -> Iterator[tuple[str, list[DetectedPrice]]]:
    """Pair each line with its prices re-based to the line (``clean`` joins the
    lines with one newline, and prices never span a line break)."""
    offset = 0
    for line in lines:
        end = offset + len(line)
        yield (
            line,
            [
                replace(price, start=price.start - offset, end=price.end - offset)
                for price in prices
                if offset <= price.start < end
            ],
        )
        offset = end + 1


def _leverage_of(clean: str) -> float | None:
    match = LEVERAGE.search(clean)
    if match is None:
        return None
    return max(float(value) for value in match.groups() if value is not None)


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
    direction = _primary_direction(clean, overlay, detections.get("directions"))
    instrument = _primary_instrument(
        clean, overlay, detections.get("instruments"), direction
    )

    prices = detections.get("prices")
    if prices is None:
        prices = detect_prices(clean)
    state = _State()
    for line, line_prices in _prices_by_line(lines, prices):
        _classify_line(line, line_prices, state, overlay)

    entry = _resolve_entry(state)
    return StructuredFields(
        instrument=instrument.normalized if instrument else None,
        instrument_raw=instrument.raw if instrument else None,
        direction=direction.normalized if direction else None,
        order_type=_order_type_for(entry),
        entry=entry,
        stop_loss=state.stop_loss,
        take_profits=state.take_profits,
        leverage=_leverage_of(clean),
    )
