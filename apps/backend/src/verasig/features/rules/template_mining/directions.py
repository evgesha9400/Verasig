"""Verasig - Template Mining: direction detection.

Words carry strong confidence; direction emojis are deliberately weak because
a coloured circle is ambiguous out of context. Both are returned in source
order so the scorer can tell "emoji-only" signals apart from worded ones.

Faithful port of ``directions.js``.
"""

from __future__ import annotations

from dataclasses import dataclass

import regex as re

from .text import escape_reg_exp

WORD_CONFIDENCE = 0.9
EMOJI_CONFIDENCE = 0.4
# Below word strength - the boundary the scorer/normalizer use to tell an
# emoji-inferred direction apart from one the author actually wrote out.
EMOJI_CONFIDENCE_CEILING = 0.7

BUY_WORDS = ["buy", "long", "bullish"]
SELL_WORDS = ["sell", "short", "bearish"]
# Russian: лонг = long/buy, шорт = short/sell.
BUY_WORDS_RU = ["лонг"]
SELL_WORDS_RU = ["шорт"]
BUY_EMOJIS = ["\U0001f7e2", "⬆", "\U0001f680", "\U0001f4c8", "\U0001f53c"]
SELL_EMOJIS = ["\U0001f534", "⬇", "\U0001f4c9", "\U0001f53d"]

# JS `\b` is ASCII-only; mirror it with explicit \w-style lookarounds.
_ASCII_WORD = "A-Za-z0-9_"


@dataclass
class DetectedEntity:
    """A detected direction with its source span."""

    raw: str
    normalized: str
    start: int
    end: int
    confidence: float


def is_emoji_direction(entity: DetectedEntity) -> bool:
    return entity.confidence < EMOJI_CONFIDENCE_CEILING


def is_emoji_only_direction(directions: list[DetectedEntity]) -> bool:
    return len(directions) > 0 and all(is_emoji_direction(d) for d in directions)


def _word_matcher(words: list[str]) -> re.Pattern:
    body = "|".join(words)
    return re.compile(
        rf"(?<![{_ASCII_WORD}])({body})(?![{_ASCII_WORD}])", re.IGNORECASE
    )


def _cyrillic_matcher(words: list[str]) -> re.Pattern:
    body = "|".join(words)
    return re.compile(rf"(?<!\p{{L}})({body})(?!\p{{L}})", re.IGNORECASE)


def _emoji_matcher(emojis: list[str]) -> re.Pattern:
    # Optional VS16 (U+FE0F) lets "⬆️" match the same rule as bare "⬆".
    body = "|".join(emojis)
    return re.compile(rf"({body})️?")


def _token_matcher(token: str) -> re.Pattern:
    body = escape_reg_exp(token)
    if re.fullmatch(r"[\p{L}]+", token):
        return re.compile(rf"(?<!\p{{L}}){body}(?!\p{{L}})", re.IGNORECASE)
    return re.compile(body)


@dataclass
class _Rule:
    matcher: re.Pattern
    normalized: str
    confidence: float


def _overlay_direction_rules(overlay: dict | None) -> list[_Rule]:
    tokens = (overlay or {}).get("directionTokens")
    if not tokens:
        return []
    return [
        _Rule(
            matcher=_token_matcher(token),
            normalized=normalized,
            confidence=WORD_CONFIDENCE,
        )
        for token, normalized in tokens.items()
    ]


# "call"/"put" are directions only in an options price context ("CALL above 210",
# "PUT 180") — bare prose ("premium leveraged calls") is NOT a direction. Require
# an adjacent price after an optional above/below/at/@. [0-9] mirrors JS `\d`.
_OPTIONS_CALL = re.compile(
    rf"(?<![{_ASCII_WORD}])(calls?)(?![{_ASCII_WORD}])"
    r"(?=\s+(?:above|below|at|@)?\s*[0-9])",
    re.IGNORECASE,
)
_OPTIONS_PUT = re.compile(
    rf"(?<![{_ASCII_WORD}])(puts?)(?![{_ASCII_WORD}])"
    r"(?=\s+(?:above|below|at|@)?\s*[0-9])",
    re.IGNORECASE,
)

RULES = [
    _Rule(_word_matcher(BUY_WORDS), "BUY", WORD_CONFIDENCE),
    _Rule(_word_matcher(SELL_WORDS), "SELL", WORD_CONFIDENCE),
    _Rule(_OPTIONS_CALL, "BUY", WORD_CONFIDENCE),
    _Rule(_OPTIONS_PUT, "SELL", WORD_CONFIDENCE),
    _Rule(_cyrillic_matcher(BUY_WORDS_RU), "BUY", WORD_CONFIDENCE),
    _Rule(_cyrillic_matcher(SELL_WORDS_RU), "SELL", WORD_CONFIDENCE),
    _Rule(_emoji_matcher(BUY_EMOJIS), "BUY", EMOJI_CONFIDENCE),
    _Rule(_emoji_matcher(SELL_EMOJIS), "SELL", EMOJI_CONFIDENCE),
]


def _rules_for(overlay: dict | None) -> list[_Rule]:
    if not (overlay or {}).get("directionTokens"):
        return RULES
    return [*RULES, *_overlay_direction_rules(overlay)]


def detect_directions(text: str, overlay: dict | None = None) -> list[DetectedEntity]:
    if not text:
        return []
    rules = _rules_for(overlay)
    hits: list[DetectedEntity] = []
    for rule in rules:
        for match in rule.matcher.finditer(text):
            hits.append(
                DetectedEntity(
                    raw=match.group(0),
                    normalized=rule.normalized,
                    start=match.start(),
                    end=match.start() + len(match.group(0)),
                    confidence=rule.confidence,
                )
            )
    hits.sort(key=lambda h: h.start)
    return hits
