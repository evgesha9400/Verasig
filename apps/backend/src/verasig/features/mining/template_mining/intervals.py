"""Verasig - Template Mining: half-open interval overlap test.

Shared by instrument and price-span dedupe, which each reserve character
ranges and need to know when two of them collide.

Faithful port of ``intervals.js``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

_Span = Any
_SpanOf = Callable[[_Span], tuple[int, int]]


def _identity(span: _Span) -> tuple[int, int]:
    return span


def intervals_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """True when ``[a_start, a_end)`` and ``[b_start, b_end)`` intersect."""
    return a_start < b_end and b_start < a_end


def overlaps_any(
    start: int,
    end: int,
    spans: Sequence[_Span],
    span_of: _SpanOf = _identity,
) -> bool:
    """True when ``[start, end)`` overlaps any span in the list."""
    for span in spans:
        span_start, span_end = span_of(span)
        if intervals_overlap(start, end, span_start, span_end):
            return True
    return False


def by_start_then_longest_key(
    span_of: _SpanOf = _identity,
) -> Callable[[_Span], tuple[int, int]]:
    """Build a ``sorted(key=...)`` matching JS ``a.start-b.start || b.end-a.end``.

    Earliest span first; ties broken longest-first, so a dedupe pass that keeps
    only the first non-overlapping span per start position prefers the one
    covering the most text.
    """

    def key(span: _Span) -> tuple[int, int]:
        start, end = span_of(span)
        return (start, -end)

    return key
