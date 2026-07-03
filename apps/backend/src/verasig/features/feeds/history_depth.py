"""How far back a fresh capture reaches (spec §4.1, ADR 0014).

A `Feed` remembers a chosen `HistoryDepth`; a fresh backfill (NULL cursor) stops
once it reaches the depth's `depth_cutoff` — the oldest `posted_at` worth
capturing. Deepening later is a `Re-fetch full history`, never a resume. Pure:
the reference `now` is injected so the cutoff is deterministic.
"""

from datetime import datetime, timedelta
from enum import StrEnum

_SIX_MONTHS = timedelta(days=183)
_ONE_YEAR = timedelta(days=365)


class HistoryDepth(StrEnum):
    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"
    ALL = "all"


def depth_cutoff(depth: HistoryDepth, now: datetime) -> datetime | None:
    """The oldest `posted_at` a fresh capture at `depth` should reach.

    `None` for `ALL` — no lower bound, capture the whole available history.
    """
    if depth is HistoryDepth.SIX_MONTHS:
        return now - _SIX_MONTHS
    if depth is HistoryDepth.ONE_YEAR:
        return now - _ONE_YEAR
    return None
