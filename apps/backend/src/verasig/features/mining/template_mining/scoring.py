"""Verasig - Template Mining: confidence scoring.

A transparent additive rubric: structural evidence adds, update/result markers
subtract, geometry contributes its own adjustment. The raw score is normalized
to 0..1. It is used for RANKING families and deciding review order - not as a
precise probability - so thresholds matter more than exact values.

Faithful port of ``scoring.js``.
"""

from __future__ import annotations

from dataclasses import dataclass

import regex as re

from .directions import detect_directions, is_emoji_only_direction
from .fields import StructuredFields
from .geometry import validate_price_geometry
from .intent import has_stop_loss, has_take_profits
from .text import normalize_message_text

# a clean, fully-structured signal lands high (~0.9) but below saturation
NORMALIZER = 16

# JS `\b` is ASCII-only; re.ASCII mirrors that boundary semantics.
_A = re.ASCII


@dataclass
class _NegativeRule:
    test: object  # Callable[[str], bool]
    penalty: int


_HIT_LEVEL = re.compile(r"\bhit\b", _A)
_LEVEL_TOKEN = re.compile(r"\b(tp\d*|sl|target)\b", _A)
_CLOSED = re.compile(r"\bclosed\b", _A)
_CLOSING = re.compile(r"\bclos(e|ing)\b", _A)
_MOVE_STOP = re.compile(r"\bmove\s*(sl|stop)\b", _A)
_BREAKEVEN = re.compile(r"\b(breakeven|break\s*even|to\s*be)\b", _A)
_CANCEL = re.compile(r"\bcancel(led)?\b", _A)
_PNL = re.compile(r"\b\d+(\.\d+)?\s*(pips?|points?|pts)\b", _A)
_IN_PROFIT = re.compile(r"\bin\s+profit\b", _A)
_MARKET = re.compile(r"\b(now|cmp|market)\b", _A)

NEGATIVE_RULES = [
    _NegativeRule(
        lambda t: bool(_HIT_LEVEL.search(t)) and bool(_LEVEL_TOKEN.search(t)), -5
    ),
    _NegativeRule(lambda t: bool(_CLOSED.search(t)), -5),
    _NegativeRule(lambda t: bool(_CLOSING.search(t)), -4),
    _NegativeRule(lambda t: bool(_MOVE_STOP.search(t)), -4),
    _NegativeRule(lambda t: bool(_BREAKEVEN.search(t)), -4),
    _NegativeRule(lambda t: bool(_CANCEL.search(t)), -4),
    # Quantified P&L or "in profit" reads as an outcome; bare "take profit" not.
    _NegativeRule(lambda t: bool(_PNL.search(t)) or bool(_IN_PROFIT.search(t)), -3),
]


def candidate_text(candidate: dict) -> str:
    message = candidate.get("message")
    if message is not None:
        text = getattr(message, "text", None)
        if text is None and isinstance(message, dict):
            text = message.get("text")
        if text is not None:
            return text
    return candidate.get("text") or ""


def _candidate_directions(candidate: dict, text: str):
    directions = candidate.get("directions")
    return directions if directions is not None else detect_directions(text)


def _candidate_normalized(candidate: dict, text: str):
    if candidate.get("lower") is not None:
        return candidate["lower"], candidate.get("lines")
    normalized = normalize_message_text(text)
    return normalized.lower, normalized.lines


def _has_structured_prices(fields: StructuredFields) -> bool:
    return bool(fields.entry or has_stop_loss(fields) or has_take_profits(fields))


def _positive_score(fields: StructuredFields, has_market: bool, line_count: int) -> int:
    score = 0
    if fields.instrument:
        score += 3
    if fields.direction:
        score += 3
    if fields.entry:
        score += 2
    if has_market:
        score += 1
    if has_stop_loss(fields):
        score += 2
    if has_take_profits(fields):
        score += 2
    if line_count <= 6 and fields.direction and _has_structured_prices(fields):
        score += 1
    return score


def _compute_negative(
    fields: StructuredFields, lower: str, has_market: bool, directions: list
) -> int:
    score = 0
    for rule in NEGATIVE_RULES:
        if rule.test(lower):
            score += rule.penalty
    if not _has_structured_prices(fields) and not has_market:
        score -= 1
    if is_emoji_only_direction(directions):
        score -= 1
    return score


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_candidate(candidate: dict) -> float:
    text = candidate_text(candidate)
    fields = candidate.get("fields") or StructuredFields()
    lower, lines = _candidate_normalized(candidate, text)
    directions = _candidate_directions(candidate, text)
    geometry = candidate.get("geometry")
    if geometry is None:
        geometry = validate_price_geometry(fields)
    has_market = bool(_MARKET.search(lower))
    line_count = len(lines) if lines is not None else 0

    raw = (
        _positive_score(fields, has_market, line_count)
        + _compute_negative(fields, lower, has_market, directions)
        + geometry.score_adjustment
    )
    return _clamp01(raw / NORMALIZER)
