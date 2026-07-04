"""Verasig - Template Mining: candidate extraction.

Assembles the detectors, extractor, intent classifier, scorer, geometry check
and template normalizer into one Candidate. The minimum bar is instrument +
direction; below it the message is not a signal candidate and we return None -
the parser itself is the classifier.

Faithful port of ``extract.js`` (the perf-only weakMemo caches are omitted;
they are an optimization, not behavior).
"""

from __future__ import annotations

from dataclasses import dataclass

from .directions import detect_directions, is_emoji_only_direction
from .fields import StructuredFields, extract_signal_fields
from .geometry import validate_price_geometry
from .instruments import detect_instruments
from .intent import classify_intent
from .prices import detect_prices
from .scoring import score_candidate
from .template import hash_string, normalize_template
from .text import normalize_message_text
from .types import Candidate, ChatMessage


@dataclass
class _Analysis:
    clean: str
    lower: str
    lines: list[str]
    instruments: list
    directions: list
    fields: StructuredFields
    intent: str


def _as_message(message) -> ChatMessage:
    # Hash the content so two distinct same-length strings get distinct ids.
    if isinstance(message, str):
        return ChatMessage(id=f"msg_{hash_string(message)}", text=message)
    if isinstance(message, dict):
        return ChatMessage(
            id=message.get("id"),
            text=message.get("text", ""),
            date=message.get("date"),
            sender=message.get("sender"),
            group_id=message.get("groupId") or message.get("group_id"),
            reply_to_message_id=(
                message.get("replyToMessageId") or message.get("reply_to_message_id")
            ),
        )
    return message


def _message_text(message) -> str:
    if isinstance(message, ChatMessage):
        return message.text
    if isinstance(message, dict):
        return message.get("text", "")
    return getattr(message, "text", "") or ""


def _intent_rejection_reason(intent: str) -> str | None:
    if intent == "update":
        return "Reads as an update to an open trade, not a new signal."
    if intent == "result":
        return "Reads as a trade result, not a new signal."
    if intent == "commentary":
        return "Reads as commentary, not a tradeable signal."
    return None


def _collect_rejection_reasons(intent, fields, directions, geometry) -> list[str]:
    reasons = [*geometry.warnings]
    intent_reason = _intent_rejection_reason(intent)
    if intent_reason:
        reasons.append(intent_reason)
    if is_emoji_only_direction(directions):
        reasons.append("Direction is inferred from an emoji only.")
    return reasons


def analyze_message(message, overlay: dict | None = None) -> _Analysis:
    """Detectors, extracted fields and intent for any message."""
    normalized = normalize_message_text(_message_text(message))
    clean, lower, lines = normalized.clean, normalized.lower, normalized.lines
    instruments = detect_instruments(clean, overlay)
    directions = detect_directions(clean, overlay)
    fields = extract_signal_fields(
        message,
        overlay,
        {
            "instruments": instruments,
            "directions": directions,
            "normalized": normalized,
        },
    )
    intent = classify_intent(_message_text(message), fields)
    return _Analysis(clean, lower, lines, instruments, directions, fields, intent)


def attempt_extract_signal(input_, overlay: dict | None = None) -> Candidate | None:
    message = _as_message(input_)
    analysis = analyze_message(message, overlay)
    if not analysis.instruments or not analysis.directions:
        return None
    # The parser is the classifier: only a message that reads as a NEW signal is
    # a candidate / template family.
    if analysis.intent != "new_signal":
        return None

    prices = detect_prices(analysis.clean)
    template = normalize_template(
        {"message": message},
        overlay,
        {
            "instruments": analysis.instruments,
            "directions": analysis.directions,
            "prices": prices,
        },
    )
    # No structural skeleton survived - it is not a parseable signal format.
    if not template.normalized_template.strip():
        return None

    geometry = validate_price_geometry(analysis.fields)
    confidence = score_candidate(
        {
            "message": message,
            "fields": analysis.fields,
            "directions": analysis.directions,
            "geometry": geometry,
            "lower": analysis.lower,
            "lines": analysis.lines,
        }
    )
    rejection_reasons = _collect_rejection_reasons(
        analysis.intent, analysis.fields, analysis.directions, geometry
    )

    return Candidate(
        message=message,
        instruments=analysis.instruments,
        directions=analysis.directions,
        prices=prices,
        fields=analysis.fields,
        intent=analysis.intent,
        confidence=confidence,
        rejection_reasons=rejection_reasons,
        parser_issues=geometry.issues,
        template_key=template.template_key,
        normalized_template=template.normalized_template,
    )
