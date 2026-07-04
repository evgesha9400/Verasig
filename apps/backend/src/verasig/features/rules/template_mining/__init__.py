"""Verasig - Template Mining: public surface of the parser-first miner.

Pure, deterministic, local. A faithful Python port of the frontend
``template-mining`` module. No LLM.

The client-only ``rules.js`` (accepted-rule audit/compile) and ``weakMemo.js``
(a perf-only cache) are intentionally not ported - mining does not need them.
"""

from __future__ import annotations

from dataclasses import asdict

from .directions import detect_directions
from .extract import analyze_message, attempt_extract_signal
from .fields import extract_signal_fields, has_trading_label
from .geometry import validate_price_geometry
from .instruments import detect_instruments
from .intent import classify_intent
from .mining import by_coverage_then_confidence, mine_template_groups
from .prices import detect_prices, parse_number
from .scoring import score_candidate
from .template import normalize_template
from .text import normalize_message_text
from .types import Candidate, ChatMessage, TemplateGroup


def template_group_to_dict(group: TemplateGroup) -> dict:
    """Convert a TemplateGroup (with nested dataclasses) to a JSON-serializable dict.

    Keys stay snake_case; a later task wraps the payload in a CamelModel for SSE.
    """
    return asdict(group)


__all__ = [
    "Candidate",
    "ChatMessage",
    "TemplateGroup",
    "analyze_message",
    "attempt_extract_signal",
    "by_coverage_then_confidence",
    "classify_intent",
    "detect_directions",
    "detect_instruments",
    "detect_prices",
    "extract_signal_fields",
    "has_trading_label",
    "mine_template_groups",
    "normalize_message_text",
    "normalize_template",
    "parse_number",
    "score_candidate",
    "template_group_to_dict",
    "validate_price_geometry",
]
