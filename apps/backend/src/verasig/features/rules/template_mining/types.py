"""Verasig - Template Mining: shared dataclasses.

Mirrors the JSDoc typedefs in ``types.js`` as Python dataclasses. Everything is
snake_case internally and JSON-serializable (a later task wraps the output in a
CamelModel for an SSE payload).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .directions import DetectedEntity as DirectionEntity
from .fields import StructuredFields
from .geometry import ParserIssue
from .instruments import DetectedEntity as InstrumentEntity
from .prices import DetectedPrice


@dataclass
class ChatMessage:
    """A raw Telegram message, the unit of input to the miner."""

    id: str
    text: str
    date: str | None = None
    sender: str | None = None
    group_id: str | None = None
    reply_to_message_id: str | None = None


@dataclass
class Candidate:
    """A message that cleared the minimum bar (instrument + direction)."""

    message: ChatMessage
    instruments: list[InstrumentEntity]
    directions: list[DirectionEntity]
    prices: list[DetectedPrice]
    fields: StructuredFields
    intent: str
    confidence: float
    rejection_reasons: list[str]
    parser_issues: list[ParserIssue]
    template_key: str
    normalized_template: str


@dataclass
class TemplateGroup:
    """A family of candidates that share one normalized template."""

    id: str
    template_key: str
    normalized_template: str
    candidates: list[Candidate]
    examples: list[Candidate]
    count: int
    date_range: dict[str, str] | None
    confidence_avg: float
    intent_distribution: dict[str, int]
    geometry_warnings: int
    status: str
    suggested_action: str
    compiled_rule: object | None = field(default=None)
