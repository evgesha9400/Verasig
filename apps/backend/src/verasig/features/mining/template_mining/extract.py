"""Verasig - Template Mining: candidate extraction.

Assembles the detectors, extractor, intent classifier, scorer, geometry check
and template normalizer into one Candidate. The minimum bar is instrument +
direction; below it the message is not a signal candidate and we return None -
the parser itself is the classifier. ``analyze_message`` is the single pass:
the text is normalized and its prices detected once, and every downstream step
reuses them.
"""

from __future__ import annotations

from dataclasses import dataclass

from .directions import detect_directions, is_emoji_only_direction
from .fields import StructuredFields, extract_signal_fields
from .geometry import validate_price_geometry
from .instruments import detect_instruments
from .intent import classify_intent
from .prices import DetectedPrice, detect_prices
from .scoring import score_candidate
from .template import hash_string, normalize_template
from .text import NormalizedText, normalize_message_text
from .types import Candidate, ChatMessage


@dataclass
class _Analysis:
    normalized: NormalizedText
    instruments: list
    directions: list
    prices: list[DetectedPrice]
    fields: StructuredFields
    intent: str

    @property
    def clean(self) -> str:
        return self.normalized.clean

    @property
    def lower(self) -> str:
        return self.normalized.lower

    @property
    def lines(self) -> list[str]:
        return self.normalized.lines


def as_message(message) -> ChatMessage:
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


def _collect_rejection_reasons(directions, geometry) -> list[str]:
    reasons = [*geometry.warnings]
    if is_emoji_only_direction(directions):
        reasons.append("Direction is inferred from an emoji only.")
    return reasons


def analyze_message(message, overlay: dict | None = None) -> _Analysis:
    """Detectors, extracted fields and intent for any message."""
    normalized = normalize_message_text(_message_text(message))
    instruments = detect_instruments(normalized.clean, overlay)
    directions = detect_directions(normalized.clean, overlay)
    prices = detect_prices(normalized.clean)
    fields = extract_signal_fields(
        message,
        overlay,
        {
            "instruments": instruments,
            "directions": directions,
            "prices": prices,
            "normalized": normalized,
        },
    )
    intent = classify_intent(normalized.original, fields, normalized)
    return _Analysis(normalized, instruments, directions, prices, fields, intent)


def attempt_extract_signal(input_, overlay: dict | None = None) -> Candidate | None:
    message = as_message(input_)
    return candidate_of(message, analyze_message(message, overlay), overlay)


def candidate_of(
    message: ChatMessage, analysis: _Analysis, overlay: dict | None = None
) -> Candidate | None:
    """The candidate an already-analyzed message yields, or None below the bar."""
    if not analysis.instruments or not analysis.directions:
        return None
    # The parser is the classifier: only a message that reads as a NEW signal is
    # a candidate / template family.
    if analysis.intent != "new_signal":
        return None

    template = normalize_template(
        {"message": message},
        overlay,
        {
            "instruments": analysis.instruments,
            "directions": analysis.directions,
            "prices": analysis.prices,
            "normalized": analysis.normalized,
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
    rejection_reasons = _collect_rejection_reasons(analysis.directions, geometry)

    return Candidate(
        message=message,
        instruments=analysis.instruments,
        directions=analysis.directions,
        prices=analysis.prices,
        fields=analysis.fields,
        intent=analysis.intent,
        confidence=confidence,
        rejection_reasons=rejection_reasons,
        parser_issues=geometry.issues,
        template_key=template.template_key,
        normalized_template=template.normalized_template,
    )
