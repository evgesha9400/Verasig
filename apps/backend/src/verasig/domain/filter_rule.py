"""Distilled candidate-inclusion rule (data-contracts.md §4; ADR 0005).

`FilterRule` is recall-first: `include_patterns` are OR-joined (ANY match → a
candidate), `exclude_patterns` are rare carve-outs (precision is recovered
downstream by extraction). Distilled from signal `GoldenLabel.label`s; shares a regex
engine with `ParserRule` but is a distinct entity (it decides inclusion).
"""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class FilterRule(BaseModel):
    rule_id: str
    user_id: UUID | None = None
    channel_id: int | None = None  # null = global / seed
    version: int = 1
    include_patterns: list[str]  # OR-joined, recall-first
    exclude_patterns: list[str] = Field(default_factory=list)
    matched_reason_template: str = "filter_rule"
    recall_target: float = 0.95
    python_filter: str | None = None  # dotted path; escape hatch
    display: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    distilled_from_label_ids: list[UUID] = Field(default_factory=list)
