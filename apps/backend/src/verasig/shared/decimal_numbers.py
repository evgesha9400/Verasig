"""Shared number parsing for noisy signal text.

`to_decimal` turns a raw price/size token into a `Decimal`, tolerating thousands
commas, internal spaces, and `k`/`m` magnitude suffixes (latin + cyrillic). It is
the single source of truth for both the deterministic parser and the lifecycle
patch classifier; an unparseable token yields `None`.
"""

from decimal import Decimal, InvalidOperation

_THOUSANDS = {"K", "К"}  # latin + cyrillic
_MILLIONS = {"M", "М"}


def to_decimal(raw: str) -> Decimal | None:
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
        value = Decimal(cleaned) * multiplier
    except InvalidOperation:
        return None
    # "nan"/"inf"/"infinity" parse as valid Decimals but are never real prices.
    return value if value.is_finite() else None
