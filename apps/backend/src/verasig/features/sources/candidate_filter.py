"""Recall-first seed candidate filter (CONTEXT.md; ADR 0005).

The cheap, cold-start heuristic that flags a `RawTelegramMessage` as an advisory
`RawSignalEvent`. It **over-includes on purpose** — precision is recovered
downstream by extraction. Three OR-joined reasons fire (in canonical order):
`DIRECTIONAL_KEYWORD` (long/short/buy/sell + RU), `SYMBOL_TOKEN` (an
Exchange-listed base coin), `PRICE_SHAPED` (trade-structure keywords/emoji or a
price-shaped number). Media-only / blank messages are never candidates.
"""

import re

from verasig.domain.event import MatchReason, MaterializationPath, RawSignalEvent
from verasig.domain.filter_rule import FilterRule
from verasig.domain.market_ports import Exchange
from verasig.domain.message import RawTelegramMessage

_DIRECTIONAL = re.compile(
    r"\b(long|short|buy|bought|sell|sold"
    r"|лонг|шорт|куп|покуп|прод|зашёл|зашел|вошёл|вошел|вышел)",
    re.IGNORECASE,
)
_STRUCTURE = re.compile(
    r"\b(entry|enter|sl|stop[\s-]?loss|stop|tp|take[\s-]?profit|target|profit"
    r"|leverage|lev|вход|захож|стоп|тейк|цел|плеч)",
    re.IGNORECASE,
)
_PRICE_TOKEN = re.compile(r"(\$\s?\d|\b\d+[.,]\d+\b|\b\d+\s?[kкmм]\b)", re.IGNORECASE)
_STRUCTURE_EMOJI = frozenset("🎯🛑📈📉🔴🟢")
_WORD_TOKEN = re.compile(r"[A-Za-z0-9/]+")


def _has_directional_keyword(text: str) -> bool:
    return _DIRECTIONAL.search(text) is not None


def _has_listed_symbol(text: str, exchange: Exchange) -> bool:
    return any(exchange.is_listed(token) for token in _WORD_TOKEN.findall(text))


def _has_price_shape(text: str) -> bool:
    if _STRUCTURE.search(text) is not None:
        return True
    if _PRICE_TOKEN.search(text) is not None:
        return True
    return any(char in _STRUCTURE_EMOJI for char in text)


def _matched_reasons(text: str, exchange: Exchange) -> list[MatchReason]:
    reasons: list[MatchReason] = []
    if _has_directional_keyword(text):
        reasons.append(MatchReason.DIRECTIONAL_KEYWORD)
    if _has_listed_symbol(text, exchange):
        reasons.append(MatchReason.SYMBOL_TOKEN)
    if _has_price_shape(text):
        reasons.append(MatchReason.PRICE_SHAPED)
    return reasons


def seed_candidate(
    message: RawTelegramMessage, exchange: Exchange
) -> RawSignalEvent | None:
    """Flag a message as an advisory candidate, or None when nothing fires."""
    if not message.text or not message.text.strip():
        return None
    reasons = _matched_reasons(message.text, exchange)
    if not reasons:
        return None
    return RawSignalEvent(
        channel_id=message.channel_id,
        message_id=message.message_id,
        candidate_text=message.text,
        materialized_by=MaterializationPath.SEED_HEURISTIC,
        matched_reasons=reasons,
    )


def apply_filter_rule(rule: FilterRule, text: str) -> bool:
    """A distilled FilterRule flags a candidate iff ANY include pattern matches
    (recall-first, OR-joined) and NO exclude carve-out matches. Pattern flags
    (e.g. inline ``(?i)``) are respected verbatim, as the distiller emits them."""
    if any(re.search(pattern, text) for pattern in rule.exclude_patterns):
        return False
    return any(re.search(pattern, text) for pattern in rule.include_patterns)
