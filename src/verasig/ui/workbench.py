"""Pure workbench view-model (kept Streamlit-free so it is unit-tested).

Assembles everything the distillation workbench shows from a corpus + labels +
the current distilled `FilterRule`: the 4 views (seed ∪ FilterRule candidates),
the recall-vs-GoldenLabel meter, the still-unlabeled residue. `ui/app.py` is the
thin Streamlit adapter that renders this and wires the label/distil widgets.
"""

from verasig.domain.filter_rule import FilterRule
from verasig.domain.label import GoldenLabel
from verasig.domain.message import RawTelegramMessage
from verasig.foundation.exchange import Exchange
from verasig.services.distillation.evaluation import evaluate
from verasig.services.distillation.workbench import partition, residue
from verasig.services.ingestion.candidate_filter import (
    apply_filter_rule,
    seed_candidate,
)


def _is_flagged(
    message: RawTelegramMessage, exchange: Exchange, filter_rules: list[FilterRule]
) -> bool:
    if not message.text:
        return False
    if seed_candidate(message, exchange) is not None:
        return True
    return any(apply_filter_rule(rule, message.text) for rule in filter_rules)


def view_model(
    messages: list[RawTelegramMessage],
    labels: list[GoldenLabel],
    filter_rule: FilterRule | None,
    parser_rules: list,
    *,
    drift_ids: set[int],
    exchange: Exchange,
    audit_size: int = 5,
) -> dict:
    rules = [filter_rule] if filter_rule else []
    candidate_ids = {m.message_id for m in messages if _is_flagged(m, exchange, rules)}
    labeled_ids = {label.message_id for label in labels}
    model = {
        "views": partition(messages, candidate_ids, drift_ids, audit_size=audit_size),
        "residue": residue(messages, labeled_ids),
        "candidate_ids": candidate_ids,
        "recall": 0.0,
        "parser_precision": 0.0,
    }
    if filter_rule is not None:
        report = evaluate(messages, labels, filter_rule, parser_rules)
        model["recall"] = report.filter_recall
        model["parser_precision"] = report.parser_precision
    return model
