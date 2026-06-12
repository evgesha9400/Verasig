"""Distilled field-extraction rule (data-contracts.md §4; ADR 0005).

`ParserRule` is precision-first: ordered `patterns` whose named groups map (via
`field_map`) onto `ExtractedSignal` fields, with `side_aliases` normalizing
direction words to `Side`. Distilled from `GoldenLabel.expected`; an optional
named `python_extractor` is the escape hatch (mirrors `FilterRule.python_filter`).
"""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field

from verasig.domain.signal import Side


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ParserRule(BaseModel):
    rule_id: str
    user_id: UUID | None = None
    channel_id: int | None = None  # null = global
    version: int = 1
    patterns: list[str]  # ordered regexes
    field_map: dict[str, str]  # named group → ExtractedSignal field
    side_aliases: dict[str, Side] = Field(default_factory=dict)
    python_extractor: str | None = None  # dotted path; escape hatch
    created_at: datetime = Field(default_factory=_now)
    distilled_from_label_ids: list[UUID] = Field(default_factory=list)
