"""Pure history-depth cutoff math (features/feeds/history_depth.py).

`depth_cutoff` turns a chosen `HistoryDepth` into the oldest `posted_at` a fresh
capture should reach: a fixed lookback before `now` (injected for determinism),
or `None` for the whole history. Zero clock, zero Telegram.
"""

from datetime import datetime, timedelta, timezone

from verasig.features.feeds.history_depth import HistoryDepth, depth_cutoff

_NOW = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)


def test_depth_wire_values_are_stable():
    assert HistoryDepth.SIX_MONTHS == "6m"
    assert HistoryDepth.ONE_YEAR == "1y"
    assert HistoryDepth.ALL == "all"


def test_six_months_cutoff_is_183_days_before_now():
    assert depth_cutoff(HistoryDepth.SIX_MONTHS, _NOW) == _NOW - timedelta(days=183)


def test_one_year_cutoff_is_365_days_before_now():
    assert depth_cutoff(HistoryDepth.ONE_YEAR, _NOW) == _NOW - timedelta(days=365)


def test_all_history_has_no_cutoff():
    assert depth_cutoff(HistoryDepth.ALL, _NOW) is None


def test_cutoff_preserves_timezone():
    cutoff = depth_cutoff(HistoryDepth.ONE_YEAR, _NOW)
    assert cutoff.tzinfo == timezone.utc
