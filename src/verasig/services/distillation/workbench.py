"""Pure distillation-workbench presenter (ADR 0005).

The 4-view workbench logic lives here so it is unit-tested independently of
Streamlit (spec §4: UI is a thin adapter). `partition` splits the corpus into
Candidates / Unflagged / ⚠ Drift / 🎲 Audit; `recall_meter` makes the advisory
gate's miss-rate visible (vs GoldenLabel); `residue` is the still-unlabeled tail
that shrinks each pass; `distil_step` runs one label→rules distillation.
"""

from dataclasses import dataclass

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel
from verasig.domain.message import RawTelegramMessage
from verasig.domain.parser_rule import ParserRule
from verasig.services.distillation.evaluation import filter_recall
from verasig.services.distillation.rule_distiller import RuleDistiller


@dataclass(frozen=True)
class WorkbenchViews:
    candidates: list[RawTelegramMessage]
    unflagged: list[RawTelegramMessage]
    drift: list[RawTelegramMessage]
    audit: list[RawTelegramMessage]


def _sample(items: list, size: int) -> list:
    # deterministic spread sample (a stable stand-in for the random audit pick)
    if not items or size <= 0:
        return []
    step = max(1, len(items) // size)
    return items[::step][:size]


def partition(
    messages: list[RawTelegramMessage],
    candidate_ids: set[int],
    drift_ids: set[int],
    *,
    audit_size: int = 5,
) -> WorkbenchViews:
    candidates = [m for m in messages if m.message_id in candidate_ids]
    unflagged = [m for m in messages if m.message_id not in candidate_ids]
    drift = [m for m in messages if m.message_id in drift_ids]
    return WorkbenchViews(candidates, unflagged, drift, _sample(unflagged, audit_size))


def residue(
    messages: list[RawTelegramMessage], labeled_ids: set[int]
) -> list[RawTelegramMessage]:
    return [m for m in messages if m.message_id not in labeled_ids]


def recall_meter(
    messages: list[RawTelegramMessage],
    labels: list[GoldenLabel],
    filter_rule: FilterRule,
) -> float:
    return filter_recall(messages, labels, filter_rule)


def distil_step(
    labels: list[GoldenLabel], distiller: RuleDistiller
) -> tuple[FilterRule, list[ParserRule]]:
    return distiller.distill_filter(labels), distiller.distill_parsers(labels)
