"""Verasig - Template Mining: grouping candidates into reviewable families.

Every message is parsed; the ones that clear the bar are bucketed by
template_key. Each family carries the stats a reviewer needs - count, average
confidence, intent mix, date range, examples - plus a suggested action so the
obviously good and obviously bad families need no thought.

Faithful port of ``mining.js``.
"""

from __future__ import annotations

from collections.abc import Callable

import regex as re

from .extract import attempt_extract_signal
from .types import Candidate, TemplateGroup

ACCEPT_CONFIDENCE = 0.6
ACCEPT_SIGNAL_SHARE = 0.6
REJECT_NONSIGNAL_SHARE = 0.5
GEOMETRY_REVIEW_SHARE = 0.3
MAX_EXAMPLES = 5

# Geometry warnings must never let a family auto-accept.
GEOMETRY_WARNING = re.compile(
    r"wrong side of entry|not (below|above) the targets", re.IGNORECASE
)

ACTION_RANK = {"review": 0, "accept": 1, "reject": 2}


def _empty_intent_distribution() -> dict[str, int]:
    return {"new_signal": 0, "update": 0, "result": 0, "commentary": 0, "unknown": 0}


def _bucket_by_template(candidates: list[Candidate]) -> dict[str, list[Candidate]]:
    buckets: dict[str, list[Candidate]] = {}
    for candidate in candidates:
        buckets.setdefault(candidate.template_key, []).append(candidate)
    return buckets


def _average_confidence(candidates: list[Candidate]) -> float:
    total = sum(candidate.confidence for candidate in candidates)
    return total / len(candidates)


def _intent_distribution(candidates: list[Candidate]) -> dict[str, int]:
    distribution = _empty_intent_distribution()
    for candidate in candidates:
        distribution[candidate.intent] += 1
    return distribution


def _date_range(candidates: list[Candidate]) -> dict[str, str] | None:
    dates = sorted(c.message.date for c in candidates if c.message.date)
    if not dates:
        return None
    return {"from": dates[0], "to": dates[-1]}


def _top_examples(candidates: list[Candidate]) -> list[Candidate]:
    return sorted(candidates, key=lambda c: -c.confidence)[:MAX_EXAMPLES]


def _geometry_warning_count(candidates: list[Candidate]) -> int:
    count = 0
    for candidate in candidates:
        if len(candidate.parser_issues or []) > 0 or any(
            GEOMETRY_WARNING.search(reason) for reason in candidate.rejection_reasons
        ):
            count += 1
    return count


def _suggest_action(
    distribution: dict[str, int],
    count: int,
    confidence_avg: float,
    geometry_warnings: int,
) -> str:
    signal_share = distribution["new_signal"] / count
    non_signal_share = (
        distribution["update"] + distribution["result"] + distribution["commentary"]
    ) / count
    # A materially geometry-broken family is downgraded to review, never accept.
    if geometry_warnings / count > GEOMETRY_REVIEW_SHARE:
        return "review"
    if signal_share >= ACCEPT_SIGNAL_SHARE and confidence_avg >= ACCEPT_CONFIDENCE:
        return "accept"
    if non_signal_share > REJECT_NONSIGNAL_SHARE:
        return "reject"
    return "review"


def by_coverage_then_confidence(
    coverage_of: Callable, confidence_of: Callable
) -> Callable:
    """Sort key builder: more coverage leads, ties broken by confidence.

    Matches the JS comparator ``coverage(b)-coverage(a) || confidence(b)-confidence(a)``
    as a ``sorted(key=...)`` tuple.
    """

    def key(item) -> tuple[float, float]:
        return (-coverage_of(item), -confidence_of(item))

    return key


_by_group_coverage = by_coverage_then_confidence(
    lambda group: group.count, lambda group: group.confidence_avg
)


def _to_group(template_key: str, candidates: list[Candidate]) -> TemplateGroup:
    count = len(candidates)
    confidence_avg = _average_confidence(candidates)
    distribution = _intent_distribution(candidates)
    geometry_warnings = _geometry_warning_count(candidates)
    return TemplateGroup(
        id=template_key,
        template_key=template_key,
        normalized_template=candidates[0].normalized_template,
        candidates=candidates,
        examples=_top_examples(candidates),
        count=count,
        date_range=_date_range(candidates),
        confidence_avg=confidence_avg,
        intent_distribution=distribution,
        geometry_warnings=geometry_warnings,
        status="unreviewed",
        suggested_action=_suggest_action(
            distribution, count, confidence_avg, geometry_warnings
        ),
    )


def _sort_groups(groups: list[TemplateGroup]) -> list[TemplateGroup]:
    # Bigger families first; ties broken by confidence, then by surfacing review
    # families ahead of already-decided ones.
    return sorted(
        groups,
        key=lambda g: (*_by_group_coverage(g), ACTION_RANK[g.suggested_action]),
    )


def mine_template_groups(
    messages: list, overlay: dict | None = None
) -> list[TemplateGroup]:
    candidates = [
        candidate
        for candidate in (
            attempt_extract_signal(message, overlay) for message in (messages or [])
        )
        if candidate is not None
    ]
    buckets = _bucket_by_template(candidates)
    groups = [_to_group(key, group) for key, group in buckets.items()]
    return _sort_groups(groups)
