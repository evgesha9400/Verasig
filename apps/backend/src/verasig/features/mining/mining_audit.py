"""Mining Audit: run accepted template families over the full message history.

Faithful port of the browser's ``rules.js`` (``compileRuleFromTemplate`` +
``applyAcceptedRules``). An accepted template family compiles into a
deterministic ``_CompiledRule``; running the compiled rules over every message
sorts each one into an audit bucket - a parsed signal, an ambiguous candidate,
a rejected update/result, a rare unaccepted format, or a partial-evidence
potential miss. No LLM.

``compute_audit`` is the one pure entry point: given the feed's messages, its
freshly-mined template groups, and the operator's accepted template keys, it
returns the same audit shape the browser used to compute client-side. The
route (``mining_routes.py``) is a thin wrapper that re-mines the feed and
calls this function.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import regex as re

from verasig.features.mining.template_mining.extract import (
    analyze_message,
    attempt_extract_signal,
)
from verasig.features.mining.template_mining.fields import (
    SignalEntry,
    has_trading_label,
)
from verasig.features.mining.template_mining.mining import (
    by_coverage_then_confidence,
    mine_template_groups,
)
from verasig.features.mining.template_mining.prices import detect_prices
from verasig.features.mining.template_mining.specificity import template_specificity
from verasig.features.mining.template_mining.subsumption import pattern_subsumes
from verasig.features.mining.template_mining.text import escape_reg_exp
from verasig.features.mining.template_mining.types import (
    Candidate,
    ChatMessage,
    TemplateGroup,
)

REJECT_PHRASES = [
    "hit tp",
    "tp hit",
    "sl hit",
    "closed",
    "close",
    "move sl",
    "move stop",
    "breakeven",
    "break even",
    "cancel",
    "running",
    "pips",
]
NON_SIGNAL_INTENTS = {"update", "result", "commentary"}

_A = re.IGNORECASE | re.ASCII


@dataclass
class ParsedSignal:
    """A candidate claimed by an accepted rule, above its confidence bar."""

    source_message_ids: list[str]
    instrument: str | None
    instrument_raw: str | None
    direction: str | None
    order_type: str | None
    entry: SignalEntry | None
    stop_loss: float | None
    take_profits: list[float]
    confidence: float
    parser_rule_id: str
    match: str  # "exact" | "fallback"
    intent: str


@dataclass
class RejectedEntry:
    """A message that read as an update/result, or tripped a reject phrase."""

    message: ChatMessage
    intent: str


@dataclass
class AuditResult:
    parsed_signals: list[ParsedSignal] = field(default_factory=list)
    ambiguous_candidates: list[Candidate] = field(default_factory=list)
    rejected_candidates: list[RejectedEntry] = field(default_factory=list)
    rare_templates: list[TemplateGroup] = field(default_factory=list)
    potential_misses: list[ChatMessage] = field(default_factory=list)


@dataclass
class _CompiledRule:
    """The subset of the browser's ``ParserRule`` the audit engine consumes -
    everything ``matchCandidate``/``routeCandidate`` reads. ``name``/``fields``/
    ``required`` are display-only in the browser and are not part of the
    categorization, so they are intentionally not ported here."""

    id: str
    template_key: str
    pattern: str
    specificity: int
    coverage: int
    confidence_avg: float
    reject_matchers: list[re.Pattern]
    confidence_threshold: float


def _derive_threshold(confidence_avg: float) -> float:
    """Sit the threshold a little under the family's average so typical members
    pass while weak outliers fall to the ambiguous queue."""
    return min(1.0, max(0.5, round(confidence_avg - 0.1, 2)))


def _phrase_matcher(phrase: str) -> re.Pattern:
    """Match on word boundaries (spaces tolerate any whitespace), so "closely"/
    "pipsqueak" do not trip the bare "close"/"pips" phrases a raw substring
    check would."""
    body = escape_reg_exp(phrase).replace(" ", r"\s+")
    return re.compile(rf"\b{body}\b", _A)


def compile_rule_from_template(
    group: TemplateGroup, overlay: dict | None = None
) -> _CompiledRule:
    overlay = overlay or {}
    override_threshold = (overlay.get("templateThresholds") or {}).get(
        group.template_key
    )
    reject_phrases = [*REJECT_PHRASES, *(overlay.get("rejectPhrases") or [])]
    return _CompiledRule(
        id=f"rule_{re.sub(r'^tpl_', '', group.template_key)}",
        template_key=group.template_key,
        pattern=group.normalized_template or "",
        specificity=template_specificity(group.normalized_template),
        coverage=group.count or 0,
        confidence_avg=group.confidence_avg,
        reject_matchers=[_phrase_matcher(phrase) for phrase in reject_phrases],
        confidence_threshold=(
            override_threshold
            if isinstance(override_threshold, int | float)
            else _derive_threshold(group.confidence_avg)
        ),
    )


# Specificity desc -> confidence desc -> coverage desc -> template_key asc
# (stable). Specificity leads so a broad pattern never outranks a specific one
# regardless of coverage.
_by_confidence_then_coverage = by_coverage_then_confidence(
    lambda rule: rule.confidence_avg or 0, lambda rule: rule.coverage or 0
)


def order_rules_by_precedence(rules: Sequence[_CompiledRule]) -> list[_CompiledRule]:
    return sorted(
        rules,
        key=lambda rule: (
            -rule.specificity,
            *_by_confidence_then_coverage(rule),
            rule.template_key,
        ),
    )


def match_candidate(
    candidate: Candidate,
    rule_by_key: dict[str, _CompiledRule],
    ordered_rules: Sequence[_CompiledRule],
) -> tuple[_CompiledRule, str] | None:
    """Claim a candidate for a rule: its exact family first (the maximally
    specific match), else the most-specific precedence-ordered rule whose
    pattern subsumes it."""
    exact = rule_by_key.get(candidate.template_key)
    if exact:
        return exact, "exact"
    for rule in ordered_rules:
        if pattern_subsumes(rule.pattern, candidate.normalized_template):
            return rule, "fallback"
    return None


def _to_parsed_signal(
    candidate: Candidate, rule: _CompiledRule, match: str
) -> ParsedSignal:
    fields = candidate.fields
    return ParsedSignal(
        source_message_ids=[candidate.message.id],
        instrument=fields.instrument,
        instrument_raw=fields.instrument_raw,
        direction=fields.direction,
        order_type=fields.order_type,
        entry=fields.entry,
        stop_loss=fields.stop_loss,
        take_profits=fields.take_profits,
        confidence=candidate.confidence,
        parser_rule_id=rule.id,
        # 'exact' = the candidate's own family; 'fallback' = recovered by a more
        # general accepted family it does not exactly match.
        match=match,
        intent=candidate.intent,
    )


def _text_has_reject_phrase(
    rule: _CompiledRule, candidate: Candidate, overlay: dict | None
) -> bool:
    lower = analyze_message(candidate.message, overlay).lower
    return any(matcher.search(lower) for matcher in rule.reject_matchers)


def _is_potential_miss(clean: str, instruments: list, directions: list) -> bool:
    """A message that names an instrument XOR a direction, or carries prices
    next to a trading label without both, is a near miss worth a human glance."""
    has_instrument = len(instruments) > 0
    has_direction = len(directions) > 0
    if has_instrument != has_direction:
        return True
    if not has_instrument and not has_direction:
        return len(detect_prices(clean)) > 0 and has_trading_label(clean)
    return False


def _route_candidate(
    candidate: Candidate,
    rule_by_key: dict[str, _CompiledRule],
    ordered_rules: Sequence[_CompiledRule],
    buckets: dict[str, list],
    overlay: dict | None,
) -> None:
    matched = match_candidate(candidate, rule_by_key, ordered_rules)
    if not matched:
        buckets["rare"].append(candidate)
        return
    rule, match = matched
    if _text_has_reject_phrase(rule, candidate, overlay):
        buckets["rejected"].append(
            RejectedEntry(message=candidate.message, intent=candidate.intent)
        )
        return
    if candidate.confidence >= rule.confidence_threshold:
        buckets["parsed"].append(_to_parsed_signal(candidate, rule, match))
        return
    buckets["ambiguous"].append(candidate)


def _route_non_candidate(
    message: ChatMessage, buckets: dict[str, list], overlay: dict | None
) -> None:
    """A non-candidate message that reads as an update/result is bucketed as
    rejected (without becoming a template family); a partial-evidence one is a
    potential miss."""
    analysis = analyze_message(message, overlay)
    if analysis.intent in NON_SIGNAL_INTENTS:
        buckets["rejected"].append(
            RejectedEntry(message=message, intent=analysis.intent)
        )
        return
    if _is_potential_miss(analysis.clean, analysis.instruments, analysis.directions):
        buckets["misses"].append(message)


def apply_accepted_rules(
    messages: Sequence, rules: Sequence[_CompiledRule], overlay: dict | None = None
) -> AuditResult:
    rule_by_key = {rule.template_key: rule for rule in rules}
    ordered_rules = order_rules_by_precedence(rules)
    buckets: dict[str, list] = {
        "parsed": [],
        "ambiguous": [],
        "rejected": [],
        "rare": [],
        "misses": [],
    }

    for message in messages or []:
        candidate = attempt_extract_signal(message, overlay)
        if candidate is None:
            _route_non_candidate(message, buckets, overlay)
            continue
        _route_candidate(candidate, rule_by_key, ordered_rules, buckets, overlay)

    return AuditResult(
        parsed_signals=buckets["parsed"],
        ambiguous_candidates=buckets["ambiguous"],
        rejected_candidates=buckets["rejected"],
        rare_templates=mine_template_groups(
            [candidate.message for candidate in buckets["rare"]], overlay
        ),
        potential_misses=buckets["misses"],
    )


def compute_audit(
    messages: Sequence,
    groups: Sequence[TemplateGroup],
    accepted_template_keys: Sequence[str],
    overlay: dict | None = None,
) -> AuditResult:
    """Keep the accepted families, compile them into rules, and run them over
    every message - the server-side twin of the browser's
    ``acceptedGroups.map(compileRuleFromTemplate)`` + ``applyAcceptedRules``."""
    accepted = set(accepted_template_keys)
    kept = [group for group in groups if group.template_key in accepted]
    rules = [compile_rule_from_template(group, overlay) for group in kept]
    return apply_accepted_rules(messages, rules, overlay)
