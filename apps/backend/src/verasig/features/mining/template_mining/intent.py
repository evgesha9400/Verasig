"""Verasig - Template Mining: intent classification.

Parse-first means the parser is the classifier: a message is a new signal only
when it parses into instrument + direction + some structure AND does not read
as an outcome report (result), a position adjustment (update), or chatter
(commentary). Markers are scored deterministically - no LLM.

A negated instruction ("do not buy BTC") is never admitted as a new signal, but
only a negation of the setup's own side counts: "Do not sell" under a LONG setup
is a reminder, not a veto. An explicit cancellation ("Cancelled") is an update
even when the message restates a complete setup.
"""

from __future__ import annotations

import regex as re

from .directions import HORIZON
from .fields import StructuredFields
from .text import NormalizedText, normalize_message_text

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

# "Do not buy" / "don't short" / "avoid entering" negate a direction; "enter"
# negates either side.
_NEGATION_EN = r"\b(?:do\s+not|don'?t|never|avoid|no)\s+"
_NEGATION_RU = r"(?<![а-яё])не\s+"
NEGATED_LONG_DIRECTION = [
    re.compile(_NEGATION_EN + r"(?:buy|long|enter)\b" + HORIZON, _A),
    re.compile(_NEGATION_RU + r"(?:покупа|лонгу|входи)", re.IGNORECASE),
]
NEGATED_SHORT_DIRECTION = [
    re.compile(_NEGATION_EN + r"(?:sell|short|enter)\b" + HORIZON, _A),
    re.compile(_NEGATION_RU + r"(?:прода|шорти|входи)", re.IGNORECASE),
]
_NEGATED_BY_SIDE = {"BUY": NEGATED_LONG_DIRECTION, "SELL": NEGATED_SHORT_DIRECTION}

# "Cancelled" / "отмена" withdraws the setup; "cancel if 4H closes below" is an
# invalidation rule inside a fresh setup, not a cancellation.
EXPLICIT_CANCEL = re.compile(
    r"(?:\bcancel(?:l?ed)?\b|(?<![а-яё])отмен(?:а|ен|ена|ено|или|яем|яю)?(?![а-яё]))"
    r"(?![^\n.]*(?:\b(?:if|when|unless)\b|если|когда))",
    re.IGNORECASE,
)

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


def classify_intent(
    text: str,
    fields: StructuredFields | None = None,
    normalized: NormalizedText | None = None,
) -> str:
    """Classify a message; pass ``normalized`` when the caller already has it."""
    lower = (normalized or normalize_message_text(text)).lower
    fields = fields or StructuredFields()
    intent = _classify(lower, fields)
    if intent == "new_signal" and _negates_own_direction(lower, fields.direction):
        return "commentary"
    return intent


def _negates_own_direction(lower: str, direction: str | None) -> bool:
    markers = _NEGATED_BY_SIDE.get(direction or "")
    if markers is None:  # no side to protect: any negated direction vetoes
        markers = [*NEGATED_LONG_DIRECTION, *NEGATED_SHORT_DIRECTION]
    return _any_match(markers, lower)


def _classify(lower: str, fields: StructuredFields) -> str:
    has_instrument = bool(fields.instrument)
    has_direction = bool(fields.direction)
    market_marker = bool(_MARKET_MARKER.search(lower)) or bool(_MARKET_RU.search(lower))

    if EXPLICIT_CANCEL.search(lower):
        return "update"
    # A fully-structured setup (instrument+direction+entry+SL+TP) is a new signal
    # even when it contains result-ish words like "target"; decide completeness
    # before the result heuristic can mislabel it.
    if _is_complete_setup(fields, market_marker):
        return "new_signal"
    if _looks_like_result(lower):
        return "result"
    if _any_match(STRONG_UPDATE_MARKERS, lower):
        return "update"
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
