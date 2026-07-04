"""Verasig - Template Mining: message text normalization.

Cleans Telegram text for deterministic detection while keeping the original
for display. Each transform is one named step; ``normalize_message_text``
assembles them.

Faithful port of ``text.js``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import regex as re

UNICODE_SPACES = re.compile("[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000\ufeff]")
DASHES = re.compile("[\u2010-\u2015\u2212]")  # hyphen, en/em dashes, minus
THOUSANDS = re.compile(r"(\d),(?=\d{3}(?:\D|$))")
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


def _strip_thousands_separators(text: str) -> str:
    previous = None
    current = text
    while current != previous:
        previous = current
        current = THOUSANDS.sub(r"\1", current)
    return current


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
    unified = _strip_thousands_separators(
        _unify_dashes(_unify_unicode_spaces(original))
    )
    lines = to_clean_lines(unified)
    clean = "\n".join(lines)
    return NormalizedText(
        original=original, clean=clean, lower=clean.lower(), lines=lines
    )
