"""Wire schemas for Mining Preview, Confirm and Audit (ADR 0015).

Confirm is miner-based: the browser reviews the mined template families and POSTs
the ``template_key``s it accepted. The backend re-mines the feed's stored messages
(byte-identical port) and persists the matching families' signals — so the confirm
wire shape carries only the accepted keys, never compiled rules or extractor code.

Preview and Audit carry the miner's full output (template families / audit
buckets), so those models mirror the ``template_mining`` dataclasses field-for-
field — each is built from its dataclass via ``model_validate(obj,
from_attributes=True)`` and serialized with ``model_dump(by_alias=True)`` for the
browser's camelCase JS shape.
"""

from typing import Any

from verasig.foundation.http.schemas import CamelModel


class MiningConfirmIn(CamelModel):
    accepted_template_keys: list[str] = []


class MiningConfirmOut(CamelModel):
    feed_status: str
    templates_accepted: int
    signals_extracted: int


class MiningConfirmedOut(CamelModel):
    accepted_template_keys: list[str] = []


class MiningAuditIn(CamelModel):
    accepted_template_keys: list[str] = []


# --- Shared building blocks (mirror template_mining/types.py + friends) -----


class ChatMessageOut(CamelModel):
    id: str
    text: str
    date: str | None = None
    sender: str | None = None
    group_id: str | None = None
    reply_to_message_id: str | None = None


class MineMessageOut(CamelModel):
    """The trimmed ``{id, text, date}`` shape the mine payload's top-level
    ``messages`` array has always carried (the browser's verify-audit preview
    input) — narrower than the full ``ChatMessageOut`` embedded in candidates."""

    id: str
    text: str
    date: str | None = None


class DetectedEntityOut(CamelModel):
    """A detected instrument or direction span — both dataclasses share this
    shape."""

    raw: str
    normalized: str
    start: int
    end: int
    confidence: float


class DetectedPriceOut(CamelModel):
    raw: str
    type: str
    start: int
    end: int
    value: float | None = None
    min: float | None = None
    max: float | None = None


class SignalEntryOut(CamelModel):
    type: str
    price: float | None = None
    min: float | None = None
    max: float | None = None
    raw: str | None = None


class StructuredFieldsOut(CamelModel):
    instrument: str | None = None
    instrument_raw: str | None = None
    direction: str | None = None
    order_type: str | None = None
    entry: SignalEntryOut | None = None
    stop_loss: float | None = None
    take_profits: list[float] = []


class ParserIssueOut(CamelModel):
    code: str
    field: str
    label: str


class CandidateOut(CamelModel):
    message: ChatMessageOut
    instruments: list[DetectedEntityOut]
    directions: list[DetectedEntityOut]
    prices: list[DetectedPriceOut]
    fields: StructuredFieldsOut
    intent: str
    confidence: float
    rejection_reasons: list[str]
    parser_issues: list[ParserIssueOut]
    template_key: str
    normalized_template: str


class TemplateGroupOut(CamelModel):
    id: str
    template_key: str
    normalized_template: str
    candidates: list[CandidateOut]
    examples: list[CandidateOut]
    count: int
    date_range: dict[str, str] | None = None
    confidence_avg: float
    intent_distribution: dict[str, int]
    geometry_warnings: int
    status: str
    suggested_action: str
    # Always None — mineTemplateGroups never sets a compiled rule; kept so the
    # wire shape matches the pre-existing (pre-CamelModel) payload exactly.
    compiled_rule: Any | None = None


# --- Mine (preview) ----------------------------------------------------------


class MineResultOut(CamelModel):
    groups: list[TemplateGroupOut]
    messages: list[MineMessageOut]


# --- Mining Audit -------------------------------------------------------------


class ParsedSignalOut(CamelModel):
    source_message_ids: list[str]
    instrument: str | None = None
    instrument_raw: str | None = None
    direction: str | None = None
    order_type: str | None = None
    entry: SignalEntryOut | None = None
    stop_loss: float | None = None
    take_profits: list[float] = []
    confidence: float
    parser_rule_id: str
    match: str
    intent: str


class RejectedEntryOut(CamelModel):
    message: ChatMessageOut
    intent: str


class MiningAuditOut(CamelModel):
    parsed_signals: list[ParsedSignalOut]
    ambiguous_candidates: list[CandidateOut]
    rejected_candidates: list[RejectedEntryOut]
    rare_templates: list[TemplateGroupOut]
    potential_misses: list[ChatMessageOut]
