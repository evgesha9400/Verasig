"""Static exchange listing adapter for the seed candidate filter.

`StaticExchange` ships a bundled cold-start seed of major base coins and
implements the pure `Exchange` seam.
"""

from verasig.domain.market_ports import Exchange

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


class StaticExchange(Exchange):
    """Cold-start seed exchange backed by a bundled base-symbol set."""

    def base_symbols(self) -> set[str]:
        return set(_SEED_BASE_SYMBOLS)

    def is_listed(self, token: str) -> bool:
        return normalize_base_symbol(token) in _SEED_BASE_SYMBOLS
