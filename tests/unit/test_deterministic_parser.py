from decimal import Decimal

from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import EntryType, Side
from verasig.services.extraction.deterministic_parser import parse

_PAT_RANGE = (
    r"(?P<symbol>[A-Za-z]{2,10})\s+(?P<side>long|short|buy|sell)"
    r".*?entry[:\s]+(?P<entry_low>[\d.,]+k?)\s*[-–]\s*(?P<entry_high>[\d.,]+k?)"
    r"(?:.*?sl[:\s]+(?P<sl>[\d.,]+k?))?(?:.*?tp[:\s]+(?P<tp>[\d.,]+k?))?"
)
_PAT_SINGLE = (
    r"(?P<symbol>[A-Za-z]{2,10})\s+(?P<side>long|short|buy|sell)"
    r"(?:.*?entry[:\s]+(?P<entry>[\d.,]+k?))?(?:.*?sl[:\s]+(?P<sl>[\d.,]+k?))?"
    r"(?:.*?tp1?[:\s]+(?P<tp>[\d.,]+k?))?(?:.*?tp2[:\s]+(?P<tp2>[\d.,]+k?))?"
)
RULE = ParserRule(
    rule_id="pilot-parser-v1",
    patterns=[_PAT_RANGE, _PAT_SINGLE],
    field_map={
        "symbol": "symbol",
        "side": "side",
        "entry": "entry",
        "entry_low": "entry_low",
        "entry_high": "entry_high",
        "sl": "stop_loss",
        "tp": "take_profit",
        "tp2": "take_profit",
    },
    side_aliases={"long": "LONG", "buy": "LONG", "short": "SHORT", "sell": "SHORT"},
)


def test_full_single_entry_signal_parses_all_fields():
    intent = parse(RULE, "BTC long entry 65000 sl 64000 tp 67000")
    assert (intent.symbol, intent.side) == ("BTCUSDT", Side.LONG)
    assert intent.entry_type is EntryType.LIMIT_SINGLE
    assert intent.entry_low == intent.entry_high == Decimal("65000")
    assert intent.stop_loss == Decimal("64000")
    assert intent.take_profits == [Decimal("67000")]


def test_market_entry_has_no_price():
    intent = parse(RULE, "ETH sell market")
    assert (intent.symbol, intent.side) == ("ETHUSDT", Side.SHORT)
    assert intent.entry_type is EntryType.MARKET
    assert intent.stop_loss is None
    assert intent.take_profits == []


def test_range_entry_sets_low_high_and_range_type():
    intent = parse(RULE, "SOL long entry 140-145 sl 135 tp 160")
    assert intent.entry_type is EntryType.LIMIT_RANGE
    assert intent.entry_low == Decimal("140")
    assert intent.entry_high == Decimal("145")
    assert intent.stop_loss == Decimal("135")


def test_multiple_take_profits_are_ordered():
    intent = parse(RULE, "BTC buy entry 65000 tp1 67000 tp2 68000")
    assert intent.side is Side.LONG
    assert intent.take_profits == [Decimal("67000"), Decimal("68000")]


def test_k_suffix_prices_expand_to_thousands():
    intent = parse(RULE, "BTC long entry 65k sl 64k tp 67k")
    assert intent.entry_low == Decimal("65000")
    assert intent.stop_loss == Decimal("64000")
    assert intent.take_profits == [Decimal("67000")]


def test_no_side_yields_no_signal():
    assert parse(RULE, "BTC looking strong today") is None


def test_unrelated_chatter_yields_no_signal():
    assert parse(RULE, "gm everyone, lovely day") is None
