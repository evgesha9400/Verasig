"""Verasig - Template Mining: price detection.

Pulls numeric levels and min/max ranges out of a message while stepping around
the things that look numeric but are not prices: numbered TP labels ("TP1"),
clock times ("08:42") and leverage ("5-10x"). Ranges are scanned first and
their spans reserved so the two levels of a range are never re-read as singles.

Faithful port of ``prices.js``.
"""

from __future__ import annotations

from dataclasses import dataclass

import regex as re

from .intervals import overlaps_any

_NUMBER = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?[kKmM]?"
# Clock times, optionally with seconds, so "08:42:15" is reserved whole and its
# ":15" tail is not read as a price.
TIME = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
# A numbered target ordinal written apart from its value ("TP 1 2340").
TARGET_ORDINAL = re.compile(
    r"\b(?:tp|tgt|targets?)\s+\d{1,2}\b(?=[\s:]*\d)", re.IGNORECASE
)
# Keycap-emoji ordinals (1️⃣ 2️⃣ …) prefix numbered target lines.
KEYCAP = re.compile("[0-9]\ufe0f?\u20e3")
SINGLE = re.compile(rf"(?<![A-Za-z\d.,])({_NUMBER})")
RANGE = re.compile(
    rf"(?<![A-Za-z\d.,])({_NUMBER})\s*(?:-|to)\s*({_NUMBER})", re.IGNORECASE
)

# Leverage ("10x") and percentages ("2%") only count when glued to the number.
TRAILING_UNIT_WORD = re.compile(r"^\s*(pips?|points?|pts|pct|percent)\b", re.IGNORECASE)
# x / Latin X / Cyrillic kha (leverage "20X"/"20kha") and % are never price levels.
_UNIT_CHAR = re.compile("[xX\u0445\u0425%]")


@dataclass
class DetectedPrice:
    """A detected price token - a single level or a min/max range."""

    raw: str
    type: str  # "single" | "range"
    start: int
    end: int
    value: float | None = None
    min: float | None = None
    max: float | None = None


def parse_number(raw) -> float:
    text = str(raw).replace(",", "").strip()
    suffix = text[-1:].lower()
    scale = 1000 if suffix == "k" else 1000000 if suffix == "m" else 1
    numeric = text if scale == 1 else text[:-1]
    return float(numeric) * scale


def _has_unit_suffix(text: str, end_index: int) -> bool:
    next_char = text[end_index] if end_index < len(text) else ""
    if _UNIT_CHAR.search(next_char):
        return True
    return bool(TRAILING_UNIT_WORD.match(text[end_index:]))


def _spans_of(regex: re.Pattern, text: str, spans: list[tuple[int, int]]) -> None:
    for match in regex.finditer(text):
        spans.append((match.start(), match.start() + len(match.group(0))))


def _blocked_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    _spans_of(TIME, text, spans)
    _spans_of(TARGET_ORDINAL, text, spans)
    _spans_of(KEYCAP, text, spans)
    return spans


def _collect_ranges(
    text: str,
    blocked: list[tuple[int, int]],
    reserved: list[tuple[int, int]],
    prices: list[DetectedPrice],
) -> None:
    for match in RANGE.finditer(text):
        end = match.start() + len(match.group(0))
        # Reserve the span unconditionally so a rejected range (leverage like
        # "5-10x") still suppresses its two numbers from the single-level scan.
        reserved.append((match.start(), end))
        if overlaps_any(match.start(), end, blocked) or _has_unit_suffix(text, end):
            continue
        a = parse_number(match.group(1))
        b = parse_number(match.group(2))
        prices.append(
            DetectedPrice(
                raw=match.group(0),
                min=min(a, b),
                max=max(a, b),
                type="range",
                start=match.start(),
                end=end,
            )
        )


def _collect_singles(
    text: str,
    blocked: list[tuple[int, int]],
    reserved: list[tuple[int, int]],
    prices: list[DetectedPrice],
) -> None:
    for match in SINGLE.finditer(text):
        end = match.start() + len(match.group(0))
        index = match.start()
        if overlaps_any(index, index + 1, blocked) or overlaps_any(
            index, index + 1, reserved
        ):
            continue
        if _has_unit_suffix(text, end):
            continue
        prices.append(
            DetectedPrice(
                raw=match.group(0),
                value=parse_number(match.group(1)),
                type="single",
                start=match.start(),
                end=end,
            )
        )


def detect_prices(text: str) -> list[DetectedPrice]:
    if not text:
        return []
    blocked = _blocked_spans(text)
    reserved: list[tuple[int, int]] = []
    prices: list[DetectedPrice] = []
    _collect_ranges(text, blocked, reserved, prices)
    _collect_singles(text, blocked, reserved, prices)
    prices.sort(key=lambda p: p.start)
    return prices
