from decimal import Decimal

from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import EntryType, ExtractionMethod, Side
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


def _event(text: str) -> RawSignalEvent:
    return RawSignalEvent(
        channel_id=7,
        message_id=1,
        candidate_text=text,
        materialized_by=MaterializationPath.SEED_HEURISTIC,
    )


def test_full_single_entry_signal_parses_all_fields():
    event = _event("BTC long entry 65000 sl 64000 tp 67000")
    signal = parse(RULE, event)
    assert (signal.symbol, signal.side) == ("BTCUSDT", Side.LONG)
    assert signal.entry_type is EntryType.LIMIT_SINGLE
    assert signal.entry_low == signal.entry_high == Decimal("65000")
    assert signal.stop_loss == Decimal("64000")
    assert signal.take_profits == [Decimal("67000")]


def test_signal_carries_event_linkage_and_method():
    event = _event("BTC long entry 65000")
    signal = parse(RULE, event)
    assert signal.event_id == event.id
    assert signal.channel_id == 7
    assert signal.rule_id == "pilot-parser-v1"
    assert signal.extraction_method is ExtractionMethod.DETERMINISTIC


def test_market_entry_has_no_price():
    signal = parse(RULE, _event("ETH sell market"))
    assert (signal.symbol, signal.side) == ("ETHUSDT", Side.SHORT)
    assert signal.entry_type is EntryType.MARKET
    assert signal.stop_loss is None
    assert signal.take_profits == []


def test_range_entry_sets_low_high_and_range_type():
    signal = parse(RULE, _event("SOL long entry 140-145 sl 135 tp 160"))
    assert signal.entry_type is EntryType.LIMIT_RANGE
    assert signal.entry_low == Decimal("140")
    assert signal.entry_high == Decimal("145")
    assert signal.stop_loss == Decimal("135")


def test_multiple_take_profits_are_ordered():
    signal = parse(RULE, _event("BTC buy entry 65000 tp1 67000 tp2 68000"))
    assert signal.side is Side.LONG
    assert signal.take_profits == [Decimal("67000"), Decimal("68000")]


def test_k_suffix_prices_expand_to_thousands():
    signal = parse(RULE, _event("BTC long entry 65k sl 64k tp 67k"))
    assert signal.entry_low == Decimal("65000")
    assert signal.stop_loss == Decimal("64000")
    assert signal.take_profits == [Decimal("67000")]


def test_no_side_yields_no_signal():
    assert parse(RULE, _event("BTC looking strong today")) is None


def test_unrelated_chatter_yields_no_signal():
    assert parse(RULE, _event("gm everyone, lovely day")) is None
