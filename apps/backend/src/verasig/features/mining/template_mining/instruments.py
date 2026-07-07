"""Verasig - Template Mining: instrument detection.

Three layers, most specific first: a curated alias dictionary, generic crypto
base/quote pairs, then forex six-letter pairs gated by known currency codes.
Aliases normalize to one canonical symbol so "GOLD" and "XAU" group together.

Dictionaries are intentionally data, not code - channel- or broker-specific
symbols extend the maps below without touching the matching logic.

Faithful port of ``instruments.js``.
"""

from __future__ import annotations

from dataclasses import dataclass

import regex as re

from .intervals import by_start_then_longest_key, overlaps_any
from .text import escape_reg_exp

CURRENCY_CODES = {"AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"}

CRYPTO_QUOTES = ["USDT", "USDC", "USD", "PERP", "BTC", "ETH"]

# canonical symbol -> alias terms that should normalize to it.
ALIASES: dict[str, list[str]] = {
    "XAUUSD": ["XAUUSD", "XAU", "GOLD"],
    "XAGUSD": ["XAGUSD", "XAG", "SILVER"],
    "EURUSD": ["EURUSD"],
    "GBPUSD": ["GBPUSD"],
    "USDJPY": ["USDJPY"],
    "GBPJPY": ["GBPJPY"],
    "AUDUSD": ["AUDUSD"],
    "USDCAD": ["USDCAD"],
    "USDCHF": ["USDCHF"],
    "NZDUSD": ["NZDUSD"],
    "EURJPY": ["EURJPY"],
    "EURGBP": ["EURGBP"],
    "BTCUSDT": ["BTCUSDT", "BTCUSD", "BITCOIN", "BTC"],
    "ETHUSDT": ["ETHUSDT", "ETHUSD", "ETHEREUM", "ETH"],
    "SOLUSDT": ["SOLUSDT", "SOL"],
    "NAS100": ["NAS100", "NASDAQ", "US100"],
    "US30": ["US30", "DOW"],
    "SPX500": ["SPX500", "SP500", "S&P500", "SPX"],
    "GER40": ["GER40", "DAX"],
    "AAPL": ["AAPL"],
    "TSLA": ["TSLA"],
    "NVDA": ["NVDA"],
    "MSFT": ["MSFT"],
}

# Bare crypto bases seen in real channels - matched case-sensitively (uppercase)
# so ordinary words like "Link" do not register as instruments.
CRYPTO_TICKERS = {
    "XRP",
    "DOGE",
    "BNB",
    "ADA",
    "AVAX",
    "LINK",
    "DOT",
    "MATIC",
    "POL",
    "TRX",
    "LTC",
    "BCH",
    "ATOM",
    "UNI",
    "TON",
    "SUI",
    "TIA",
    "WIF",
    "ORDI",
    "SEI",
    "ARB",
    "OP",
    "INJ",
    "NEAR",
    "PEPE",
    "SHIB",
    "BONK",
    "FLOKI",
    "APT",
    "FIL",
    "AAVE",
    "RNDR",
    "RENDER",
    "FET",
    "ICP",
    "HBAR",
    "XLM",
    "ALGO",
    "EGLD",
    "SAND",
    "MANA",
    "AXS",
    "GALA",
    "FARTCOIN",
    "NOT",
    "JUP",
    "PYTH",
    "WLD",
    "ENA",
    "ONDO",
}

DICTIONARY_CONFIDENCE = 0.95
PAIR_CONFIDENCE = 0.85

# Russian "Монета:/Монету:" coin label -> the ticker that follows.
# Allow a #/$ prefix and digits in the ticker so "#1INCH" / "1000PEPE" are caught.
COIN_LABEL = re.compile(r"Монет[а-яё]*\s*:?\s*[#$]?([A-Za-z0-9]{2,10})", re.IGNORECASE)
# A bare ticker, optionally carrying a concatenated crypto quote ("LINKUSDT"), so
# a slash-less pair still splits into base + quote instead of being swallowed
# whole. Non-greedy base + longest-first quote alternation keeps the split at the
# quote boundary (LINK|USDT, not LINKUSD|T).
BARE_TICKER = re.compile(
    r"(?<![A-Za-z0-9])([A-Z]{2,8}?)(USDT|USDC|USD|PERP|BTC|ETH)?(?![A-Za-z0-9])"
)
HAS_LETTER = re.compile(r"[A-Za-z]")


@dataclass
class _AliasRule:
    matcher: re.Pattern
    normalized: str
    source: str


@dataclass
class _Hit:
    start: int
    end: int
    normalized: str
    raw: str
    confidence: float


@dataclass
class DetectedEntity:
    """A detected primitive entity (instrument) with its source span."""

    raw: str
    normalized: str
    start: int
    end: int
    confidence: float


def _to_usdt(ticker: str) -> str:
    upper = ticker.upper()
    return upper if upper.endswith("USDT") else f"{upper}USDT"


def _alias_source(term: str) -> str:
    return f"(?<![A-Za-z0-9]){escape_reg_exp(term)}(?![A-Za-z0-9])"


def _alias_matcher(term: str) -> re.Pattern:
    return re.compile(_alias_source(term), re.IGNORECASE)


def _build_alias_rules() -> list[_AliasRule]:
    rules: list[_AliasRule] = []
    for normalized, terms in ALIASES.items():
        for term in terms:
            rules.append(
                _AliasRule(
                    matcher=_alias_matcher(term),
                    normalized=normalized,
                    source=_alias_source(term),
                )
            )
    # Longer aliases first so "BTCUSDT" wins over the "BTC" substring rule.
    # Python's sort is stable, matching JS Array.sort ties.
    rules.sort(key=lambda rule: -len(rule.source))
    return rules


ALIAS_RULES = _build_alias_rules()

CRYPTO_PAIR = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z0-9]{2,8})\s*/\s*("
    + "|".join(CRYPTO_QUOTES)
    + r")(?![A-Za-z0-9])",
    re.IGNORECASE,
)
FOREX_PAIR = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{3})([A-Za-z]{3})(?![A-Za-z0-9])")


def _collect_alias_hits(text: str, hits: list[_Hit], rules: list[_AliasRule]) -> None:
    for rule in rules:
        for match in rule.matcher.finditer(text):
            hits.append(
                _Hit(
                    start=match.start(),
                    end=match.start() + len(match.group(0)),
                    normalized=rule.normalized,
                    raw=match.group(0),
                    confidence=DICTIONARY_CONFIDENCE,
                )
            )


def _alias_rules_with(overlay: dict | None) -> list[_AliasRule]:
    aliases = (overlay or {}).get("instrumentAliases")
    if not aliases:
        return ALIAS_RULES
    extra = [
        _AliasRule(
            matcher=_alias_matcher(term),
            normalized=normalized,
            source=_alias_source(term),
        )
        for term, normalized in aliases.items()
    ]
    combined = [*extra, *ALIAS_RULES]
    combined.sort(key=lambda rule: -len(rule.source))
    return combined


def _is_valid_crypto_pair(base: str, quote: str) -> bool:
    return (
        base != quote and base not in CURRENCY_CODES and bool(HAS_LETTER.search(base))
    )


def _is_valid_forex_pair(base: str, quote: str) -> bool:
    return base in CURRENCY_CODES and quote in CURRENCY_CODES and base != quote


def _collect_pair_hits(regex, text, hits, is_valid_pair) -> None:
    for match in regex.finditer(text):
        base = match.group(1).upper()
        quote = match.group(2).upper()
        if not is_valid_pair(base, quote):
            continue
        hits.append(
            _Hit(
                start=match.start(),
                end=match.start() + len(match.group(0)),
                normalized=f"{base}{quote}",
                raw=match.group(0),
                confidence=PAIR_CONFIDENCE,
            )
        )


def _collect_coin_label_hits(text: str, hits: list[_Hit]) -> None:
    for match in COIN_LABEL.finditer(text):
        if not HAS_LETTER.search(match.group(1)):
            continue  # skip "Монета: 100" style numerics
        start, end = match.span(1)
        hits.append(
            _Hit(
                start=start,
                end=end,
                normalized=_to_usdt(match.group(1)),
                raw=match.group(1),
                confidence=DICTIONARY_CONFIDENCE,
            )
        )


def _collect_bare_ticker_hits(text: str, hits: list[_Hit]) -> None:
    for match in BARE_TICKER.finditer(text):
        base = match.group(1)
        if base not in CRYPTO_TICKERS:
            continue
        quote = match.group(2)
        hits.append(
            _Hit(
                start=match.start(),
                end=match.start() + len(match.group(0)),
                # an explicit concatenated quote is kept verbatim (LINKUSDT,
                # ETHBTC); a bare base defaults to the USDT quote, as before.
                normalized=f"{base}{quote}" if quote else _to_usdt(base),
                raw=match.group(0),
                confidence=PAIR_CONFIDENCE,
            )
        )


def _dedupe_hits(hits: list[_Hit]) -> list[_Hit]:
    ordered = sorted(hits, key=by_start_then_longest_key(lambda h: (h.start, h.end)))
    accepted: list[_Hit] = []
    seen_symbols: set[str] = set()
    for hit in ordered:
        if hit.normalized in seen_symbols:
            continue
        if overlaps_any(hit.start, hit.end, accepted, lambda h: (h.start, h.end)):
            continue
        accepted.append(hit)
        seen_symbols.add(hit.normalized)
    return accepted


def detect_instruments(text: str, overlay: dict | None = None) -> list[DetectedEntity]:
    if not text:
        return []
    hits: list[_Hit] = []
    _collect_alias_hits(text, hits, _alias_rules_with(overlay))
    _collect_coin_label_hits(text, hits)
    _collect_pair_hits(CRYPTO_PAIR, text, hits, _is_valid_crypto_pair)
    _collect_pair_hits(FOREX_PAIR, text, hits, _is_valid_forex_pair)
    _collect_bare_ticker_hits(text, hits)
    return [
        DetectedEntity(
            raw=hit.raw,
            normalized=hit.normalized,
            start=hit.start,
            end=hit.end,
            confidence=hit.confidence,
        )
        for hit in _dedupe_hits(hits)
    ]
