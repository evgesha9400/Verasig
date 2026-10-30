"""Verasig - Template Mining: message text normalization.

Cleans Telegram text for deterministic detection while keeping the original
for display. Each transform is one named step; ``normalize_message_text``
assembles them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import regex as re

UNICODE_SPACES = re.compile("[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000\ufeff]")
DASHES = re.compile("[\u2010-\u2015\u2212]")  # hyphen, en/em dashes, minus
# "64,000" -> "64000": a comma followed by exactly three digits.
THOUSANDS = re.compile(r"(\d),(?=\d{3}(?!\d))")
# Decimal commas: "0,125" -> "0.125", "12,5" -> "12.5", "2,5445" -> "2.5445".
# A comma list ("1,2,3") is left alone; a long fraction needs a short integer
# part so a bare list "64000,65000" is not read as one decimal.
ZERO_DECIMAL_COMMA = re.compile(r"(?<![\d.,])0,(?=\d+(?![\d,]))")
DECIMAL_COMMA = re.compile(
    r"(?<![\d.,])(\d+),(?=\d{1,2}(?![\d,]))"
    r"|(?<![\d.,])(\d{1,3}),(?=\d{4,}(?![\d,]))"
)
_INLINE_WHITESPACE = re.compile(r"[ \t]+")
_LINE_SPLIT = re.compile(r"\r?\n")
_REGEXP_META = re.compile(r"[.*+?^${}()|[\]\\]")


@dataclass
class NormalizedText:
    """Whitespace/number-normalized view of a message, original kept for display."""

    original: str
    clean: str
    lower: str
    lines: list[str] = field(default_factory=list)


def _unify_unicode_spaces(text: str) -> str:
    return UNICODE_SPACES.sub(" ", text)


def _unify_dashes(text: str) -> str:
    return DASHES.sub("-", text)


def _normalize_number_commas(text: str) -> str:
    current = ZERO_DECIMAL_COMMA.sub("0.", text)
    previous = None
    while current != previous:
        previous = current
        current = THOUSANDS.sub(r"\1", current)
    return DECIMAL_COMMA.sub(lambda m: f"{m.group(1) or m.group(2)}.", current)


def to_clean_lines(text: str) -> list[str]:
    lines = []
    for line in _LINE_SPLIT.split(text):
        collapsed = _INLINE_WHITESPACE.sub(" ", line).strip()
        if collapsed:
            lines.append(collapsed)
    return lines


def escape_reg_exp(text: str) -> str:
    """Escape regex metacharacters so a literal string can be embedded."""
    return _REGEXP_META.sub(lambda m: "\\" + m.group(0), text)


def normalize_message_text(text: str) -> NormalizedText:
    original = text if isinstance(text, str) else ""
    unified = _normalize_number_commas(_unify_dashes(_unify_unicode_spaces(original)))
    lines = to_clean_lines(unified)
    clean = "\n".join(lines)
    return NormalizedText(
        original=original, clean=clean, lower=clean.lower(), lines=lines
    )
