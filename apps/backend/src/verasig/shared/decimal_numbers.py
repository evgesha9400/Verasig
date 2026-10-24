"""Shared number parsing for noisy signal text.

`to_decimal` turns a raw price/size token into a `Decimal`, tolerating thousands
commas, decimal commas ("0,20" = 0.20), internal spaces, and `k`/`m` magnitude
suffixes (latin + cyrillic). It is
the single source of truth for both the deterministic parser and the lifecycle
patch classifier; an unparseable token yields `None`.
"""

import re
from decimal import Decimal, InvalidOperation

_THOUSANDS = {"K", "К"}  # latin + cyrillic
_MILLIONS = {"M", "М"}

_SUFFIX = "[kmкм]?"
# "1,000" / "65,000.5" group thousands: a non-zero lead of 1-3 digits, then
# exact 3-digit groups. "0,005" has a zero lead, so it is a decimal comma.
_THOUSANDS_GROUPED = re.compile(
    rf"[+-]?[1-9]\d{{0,2}}(?:,\d{{3}})+(?:\.\d+)?{_SUFFIX}", re.IGNORECASE
)
# "0,20" / "1,25" / "0,005": one comma between digits is a decimal separator.
_DECIMAL_COMMA = re.compile(rf"[+-]?\d+,\d+{_SUFFIX}", re.IGNORECASE)


def _normalize_commas(text: str) -> str:
    if _THOUSANDS_GROUPED.fullmatch(text):
        return text.replace(",", "")
    if _DECIMAL_COMMA.fullmatch(text):
        return text.replace(",", ".")
    return text.replace(",", "")  # a stray trailing comma ("67000,")


def to_decimal(raw: str) -> Decimal | None:
    cleaned = _normalize_commas(raw.strip().replace(" ", ""))
    if not cleaned:
        return None
    suffix = cleaned[-1].upper()
    multiplier = Decimal(1)
    if suffix in _THOUSANDS:
        multiplier, cleaned = Decimal(1000), cleaned[:-1]
    elif suffix in _MILLIONS:
        multiplier, cleaned = Decimal(1_000_000), cleaned[:-1]
    try:
        value = Decimal(cleaned) * multiplier
    except InvalidOperation:
        return None
    # "nan"/"inf"/"infinity" parse as valid Decimals but are never real prices.
    return value if value.is_finite() else None
