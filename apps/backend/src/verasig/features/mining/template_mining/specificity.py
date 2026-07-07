"""Verasig - Template Mining: template specificity.

How much literal structure a normalized skeleton carries. Used to order
accepted rules so the MOST specific family claims a message first, and so a
generalized (wildcarded) pattern can never outrank a literal one.

Faithful port of ``specificity.js``.
"""

from __future__ import annotations

from .skeleton_tokens import TOKEN


def template_specificity(skeleton: str | None) -> int:
    """+1 per structural word / value placeholder, -1 per ``<*>``."""
    tokens = TOKEN.findall(skeleton or "")
    score = 0
    for token in tokens:
        score += -1 if token == "<*>" else 1
    return score
