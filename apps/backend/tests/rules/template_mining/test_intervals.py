"""Parity port covering ``intervals.js`` helpers."""

from verasig.features.rules.template_mining.intervals import (
    by_start_then_longest_key,
    intervals_overlap,
    overlaps_any,
)


def test_intervals_overlap_true_when_they_intersect():
    assert intervals_overlap(0, 5, 3, 8) is True


def test_intervals_overlap_false_when_touching_at_the_boundary():
    # half-open: [0,5) and [5,10) do not intersect
    assert intervals_overlap(0, 5, 5, 10) is False


def test_intervals_overlap_false_when_disjoint():
    assert intervals_overlap(0, 2, 4, 6) is False


def test_overlaps_any_over_tuple_spans():
    spans = [(0, 3), (10, 12)]
    assert overlaps_any(2, 5, spans) is True
    assert overlaps_any(4, 9, spans) is False


def test_overlaps_any_with_custom_extractor():
    spans = [{"start": 0, "end": 3}]
    assert overlaps_any(1, 2, spans, lambda s: (s["start"], s["end"])) is True


def test_by_start_then_longest_orders_earliest_then_longest():
    spans = [(5, 8), (0, 2), (0, 6)]
    ordered = sorted(spans, key=by_start_then_longest_key())
    assert ordered == [(0, 6), (0, 2), (5, 8)]
