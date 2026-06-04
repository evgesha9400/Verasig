"""Deterministic ParserRule application (data-contracts.md §3; plan Slice 4).

`parse` applies a `ParserRule`'s ordered regexes to a message's candidate text
and maps the named groups (via `field_map`) onto a provenance-free `TradeIntent`.
Required = symbol + side (side normalized via `side_aliases`; symbol normalized
by `TradeIntent`); absent entry price ⇒ `MARKET`; a low/high pair ⇒ `LIMIT_RANGE`;
a single ⇒ `LIMIT_SINGLE`. No match (or missing symbol/side) ⇒ `None` (the caller
links provenance and records the outcome). Pure and offline.
"""

import re
from decimal import Decimal, InvalidOperation

from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import EntryType, Side, TradeIntent

_THOUSANDS = {"K", "К"}  # latin + cyrillic
_MILLIONS = {"M", "М"}


def _to_decimal(raw: str) -> Decimal | None:
    cleaned = raw.strip().replace(",", "").replace(" ", "")
    if not cleaned:
        return None
    suffix = cleaned[-1].upper()
    multiplier = Decimal(1)
    if suffix in _THOUSANDS:
        multiplier, cleaned = Decimal(1000), cleaned[:-1]
    elif suffix in _MILLIONS:
        multiplier, cleaned = Decimal(1_000_000), cleaned[:-1]
    try:
        return Decimal(cleaned) * multiplier
    except InvalidOperation:
        return None


def _first(groups: dict, field_map: dict[str, str], target: str) -> str | None:
    for group, mapped in field_map.items():
        if mapped == target and groups.get(group):
            return groups[group]
    return None


def _all(groups: dict, field_map: dict[str, str], target: str) -> list[str]:
    return [
        groups[group]
        for group, mapped in field_map.items()
        if mapped == target and groups.get(group)
    ]


def _entry(
    groups: dict, field_map: dict[str, str]
) -> tuple[Decimal | None, Decimal | None, EntryType]:
    low = _first(groups, field_map, "entry_low")
    high = _first(groups, field_map, "entry_high")
    if low and high:
        return _to_decimal(low), _to_decimal(high), EntryType.LIMIT_RANGE
    single = _first(groups, field_map, "entry")
    if single:
        price = _to_decimal(single)
        return price, price, EntryType.LIMIT_SINGLE
    return None, None, EntryType.MARKET


def _build_signal(rule: ParserRule, groups: dict) -> TradeIntent | None:
    symbol_raw = _first(groups, rule.field_map, "symbol")
    side_raw = _first(groups, rule.field_map, "side")
    if not symbol_raw or not side_raw:
        return None
    side: Side | None = rule.side_aliases.get(side_raw.lower())
    if side is None:
        return None
    entry_low, entry_high, entry_type = _entry(groups, rule.field_map)
    stop_raw = _first(groups, rule.field_map, "stop_loss")
    return TradeIntent(
        symbol=symbol_raw,
        side=side,
        entry_type=entry_type,
        entry_low=entry_low,
        entry_high=entry_high,
        stop_loss=_to_decimal(stop_raw) if stop_raw else None,
        take_profits=[
            price
            for raw in _all(groups, rule.field_map, "take_profit")
            if (price := _to_decimal(raw)) is not None
        ],
    )


def parse(rule: ParserRule, candidate_text: str) -> TradeIntent | None:
    for pattern in rule.patterns:
        match = re.search(pattern, candidate_text, re.IGNORECASE | re.DOTALL)
        if match is None:
            continue
        intent = _build_signal(rule, match.groupdict())
        if intent is not None:
            return intent
    return None
