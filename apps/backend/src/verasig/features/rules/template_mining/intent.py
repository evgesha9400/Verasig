"""Verasig - Template Mining: intent classification.

Parse-first means the parser is the classifier: a message is a new signal only
when it parses into instrument + direction + some structure AND does not read
as an outcome report (result), a position adjustment (update), or chatter
(commentary). Markers are scored deterministically - no LLM.

Faithful port of ``intent.js``.
"""

from __future__ import annotations

import regex as re

from .fields import StructuredFields
from .text import normalize_message_text

# JS `\b` is ASCII-only; re.ASCII mirrors that boundary semantics.
_A = re.ASCII

# Outcome reports: a trade that already played out.
RESULT_MARKERS = [
    re.compile(r"\bclosed\b", _A),
    re.compile(r"\bstopped(\s*out)?\b", _A),
    re.compile(r"\brunning\b", _A),
    re.compile(r"\b(tp\s*hit|sl\s*hit)\b", _A),
    re.compile(r"\b\d+(\.\d+)?\s*(pips?|points?|pts)\b", _A),
    re.compile(r"\b(banked|secured|booked|locked|took)\s+profits?\b", _A),
    re.compile(r"\bin\s+profit\b", _A),
    re.compile(r"\bsmashed\b", _A),
    re.compile(r"\bbanked\b", _A),
    re.compile(r"[+\-−]\d+(\.\d+)?\s*%"),
    # Russian outcome markers.
    re.compile(r"результат", re.IGNORECASE),
    re.compile(r"заработано", re.IGNORECASE),
    re.compile(r"принесла", re.IGNORECASE),
]
HIT_NEAR_LEVEL = re.compile(r"\bhit\b", _A)

STRONG_UPDATE_MARKERS = [
    re.compile(r"\bmove\b[^\n]{0,15}\b(sl|stop)\b", _A),
    re.compile(r"\bbreak\s*even\b", _A),
    re.compile(r"\bbreakeven\b", _A),
    re.compile(r"\bto\s*be\b", _A),
    re.compile(r"\bcancel(led)?\b", _A),
    re.compile(r"\bdelete\b", _A),
    re.compile(r"\baverag(e|ing)\b", _A),
    re.compile(r"\b(activated|triggered)\b", _A),
]
SOFT_UPDATE_MARKERS = [
    re.compile(
        r"\bhold\s+(the\s+)?(trade|position|runner|runners|it|longs?|shorts?)\b", _A
    ),
    re.compile(r"\bpartial(ly)?\b", _A),
    re.compile(r"\bclos(e|ing)\b", _A),
    re.compile(r"\bsecure(d)?\s+(profits?|gains?|partial|the\s+(bag|runner))\b", _A),
]

COMMENTARY_MARKERS = [
    re.compile(r"\blooks?\b", _A),
    re.compile(r"\bmaybe\b", _A),
    re.compile(r"\bmight\b", _A),
    re.compile(r"\bcould\b", _A),
    re.compile(r"\bshould\b", _A),
    re.compile(r"\bwait(ing)?\b", _A),
    re.compile(r"\bthinking\b", _A),
    re.compile(r"\banalysis\b", _A),
    re.compile(r"\bbias\b", _A),
    re.compile(r"\bexpect(ing)?\b", _A),
    re.compile(r"\bprobably\b", _A),
    re.compile(r"\bwatching\b", _A),
    re.compile(r"\bmay\b", _A),
]

LEVEL_NEARBY = re.compile(r"\b(tp\d*|sl|target)\b", _A)
_MARKET_MARKER = re.compile(r"\b(now|cmp|market)\b", _A)
_MARKET_RU = re.compile(r"по\s*рынк", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")


def _any_match(markers: list[re.Pattern], text: str) -> bool:
    return any(marker.search(text) for marker in markers)


def _looks_like_result(text: str) -> bool:
    if _any_match(RESULT_MARKERS, text):
        return True
    return bool(HIT_NEAR_LEVEL.search(text)) and bool(LEVEL_NEARBY.search(text))


def has_stop_loss(fields: StructuredFields) -> bool:
    return fields.stop_loss is not None


def has_take_profits(fields: StructuredFields) -> bool:
    return isinstance(fields.take_profits, list) and len(fields.take_profits) > 0


def _structure_score(fields: StructuredFields) -> int:
    score = 0
    if fields.entry:
        score += 1
    if has_stop_loss(fields):
        score += 1
    if has_take_profits(fields):
        score += 1
    return score


def _is_complete_setup(fields: StructuredFields, market_marker: bool) -> bool:
    return (
        bool(fields.instrument)
        and bool(fields.direction)
        and bool(fields.entry or market_marker)
        and has_stop_loss(fields)
        and has_take_profits(fields)
    )


def classify_intent(text: str, fields: StructuredFields | None = None) -> str:
    if fields is None:
        fields = StructuredFields()
    lower = normalize_message_text(text).lower
    has_instrument = bool(fields.instrument)
    has_direction = bool(fields.direction)
    market_marker = bool(_MARKET_MARKER.search(lower)) or bool(_MARKET_RU.search(lower))

    if _looks_like_result(lower):
        return "result"
    if _any_match(STRONG_UPDATE_MARKERS, lower):
        return "update"
    if _is_complete_setup(fields, market_marker):
        return "new_signal"
    if _any_match(SOFT_UPDATE_MARKERS, lower):
        return "update"

    structured = _structure_score(fields) > 0 or market_marker
    if has_instrument and has_direction and structured:
        return "new_signal"
    if _any_match(COMMENTARY_MARKERS, lower) or "?" in lower:
        return "commentary"
    word_count = len([w for w in _WHITESPACE.split(lower) if w])
    if has_instrument and has_direction and word_count <= 3:
        return "new_signal"
    if has_instrument and has_direction:
        return "commentary"
    return "unknown"
