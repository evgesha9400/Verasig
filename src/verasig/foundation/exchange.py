"""Exchange-listing seam for the seed candidate filter (spec §6; ADR 0005).

`Exchange` is the Protocol the recall-first seed heuristic codes against to ask
"is this token a listed base coin?" (the `SYMBOL_TOKEN` reason). `StaticExchange`
ships a bundled cold-start seed of major base coins; the real `BybitExchange`
(httpx over the public instruments-info endpoint) arrives with market data in
Slice 9. Tests inject a `FakeExchange`. A distilled `FilterRule` supersedes the
seed once the operator has labeled a channel.
"""

from typing import Protocol, runtime_checkable

_QUOTE_SUFFIXES = ("USDT", "USDC", "USD", "PERP")

# Bundled cold-start seed: major Bybit linear-perp base coins (recall-first; the
# distilled FilterRule replaces this once a channel is labeled).
_SEED_BASE_SYMBOLS = frozenset(
    {
        "BTC",
        "ETH",
        "SOL",
        "BNB",
        "XRP",
        "ADA",
        "DOGE",
        "AVAX",
        "LINK",
        "DOT",
        "MATIC",
        "TRX",
        "LTC",
        "BCH",
        "ATOM",
        "UNI",
        "ETC",
        "XLM",
        "NEAR",
        "APT",
        "FIL",
        "ARB",
        "OP",
        "INJ",
        "SUI",
        "SEI",
        "TIA",
        "RUNE",
        "AAVE",
        "MKR",
        "LDO",
        "GRT",
        "SAND",
        "MANA",
        "AXS",
        "APE",
        "GALA",
        "CHZ",
        "ENS",
        "DYDX",
        "FTM",
        "ALGO",
        "EGLD",
        "FLOW",
        "XTZ",
        "THETA",
        "EOS",
        "KAVA",
        "ZEC",
        "DASH",
        "SHIB",
        "PEPE",
        "WIF",
        "BONK",
        "FLOKI",
        "ORDI",
        "JTO",
        "PYTH",
        "JUP",
        "STX",
        "IMX",
        "RNDR",
        "FET",
        "AGIX",
        "OCEAN",
        "WLD",
        "BLUR",
        "GMX",
        "SNX",
        "CRV",
        "COMP",
        "1INCH",
        "SUSHI",
        "YFI",
        "ICP",
        "HBAR",
        "VET",
        "QNT",
        "TON",
        "KAS",
    }
)


def normalize_base_symbol(token: str) -> str:
    """Reduce a raw text token (`$BTC`, `BTCUSDT`, `eth/usdt`) to its base coin."""
    base = token.upper().lstrip("$#").split("/")[0].split("-")[0]
    for suffix in _QUOTE_SUFFIXES:
        if base.endswith(suffix) and len(base) > len(suffix):
            return base[: -len(suffix)]
    return base


@runtime_checkable
class Exchange(Protocol):
    def is_listed(self, token: str) -> bool: ...
    def base_symbols(self) -> set[str]: ...


class StaticExchange:
    """Cold-start seed exchange backed by a bundled base-symbol set."""

    def base_symbols(self) -> set[str]:
        return set(_SEED_BASE_SYMBOLS)

    def is_listed(self, token: str) -> bool:
        return normalize_base_symbol(token) in _SEED_BASE_SYMBOLS
