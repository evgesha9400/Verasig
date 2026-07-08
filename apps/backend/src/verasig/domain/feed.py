"""Feed lifecycle contracts — the status a followed stream moves through and the
history depth a backfill targets. These StrEnums are the single source of truth;
the DB CHECK constraints on `feed` are generated from them (see models.enum_check),
and every writer/reader routes through them instead of bare string literals."""

from enum import StrEnum


class FeedStatus(StrEnum):
    NEW = "new"
    BACKFILLING = "backfilling"
    BACKFILLED = "backfilled"
    VERIFIED = "verified"
    ANALYZED = "analyzed"
    CANCELLED = "cancelled"
    FAILED = "failed"


# Statuses in which a feed has been reviewed/confirmed by the operator — its
# verification survives a refresh and it exposes signals + deletion rescans.
REVIEWED_STATUSES = frozenset({FeedStatus.VERIFIED, FeedStatus.ANALYZED})


class HistoryDepth(StrEnum):
    """How far back a fresh capture reaches (the cutoff logic lives in the feeds
    feature; this is the canonical enum, reused by the DB CHECK on `feed`)."""

    SIX_MONTHS = "6m"
    ONE_YEAR = "1y"
    ALL = "all"
