from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import (
    ExtractedSignal,
    ExtractionMethod,
    Side,
    UnrecognizedSignal,
)
from verasig.services.extraction.extract_service import ExtractService

RULE = ParserRule(
    rule_id="r1",
    patterns=[
        r"(?P<symbol>[A-Za-z]{2,10})\s+(?P<side>long|short|buy|sell)"
        r"(?:.*?entry[:\s]+(?P<entry>[\d.,]+k?))?"
    ],
    field_map={"symbol": "symbol", "side": "side", "entry": "entry"},
    side_aliases={"long": "LONG", "short": "SHORT", "buy": "LONG", "sell": "SHORT"},
)


def _event(text: str) -> RawSignalEvent:
    return RawSignalEvent(
        channel_id=7,
        message_id=1,
        candidate_text=text,
        materialized_by=MaterializationPath.SEED_HEURISTIC,
    )


def test_signal_carries_event_linkage_and_method():
    event = _event("BTC long entry 65000")
    signal = ExtractService(rules=[RULE]).extract(event).signal
    assert signal.event_id == event.id
    assert signal.channel_id == 7
    assert signal.rule_id == "r1"
    assert signal.extraction_method is ExtractionMethod.DETERMINISTIC


def test_match_yields_exactly_one_signal_outcome():
    outcome = ExtractService(rules=[RULE]).extract(_event("BTC long entry 65000"))
    assert isinstance(outcome.signal, ExtractedSignal)
    assert outcome.signal.side is Side.LONG
    assert outcome.unrecognized is None
    assert outcome.drift_warnings == []


def test_miss_yields_unrecognized_with_no_match_reason_and_linkage():
    event = _event("gm frens wagmi")
    outcome = ExtractService(rules=[RULE]).extract(event)
    assert outcome.signal is None
    assert isinstance(outcome.unrecognized, UnrecognizedSignal)
    assert outcome.unrecognized.reason == "no_match"
    assert outcome.unrecognized.event_id == event.id
    assert outcome.unrecognized.attempted_methods == [ExtractionMethod.DETERMINISTIC]


def test_empty_rules_yield_unrecognized():
    outcome = ExtractService(rules=[]).extract(_event("BTC long entry 65000"))
    assert outcome.signal is None
    assert outcome.unrecognized is not None


def test_outcome_is_exactly_one_of_signal_or_unrecognized():
    for text in ("BTC long entry 65000", "gm frens"):
        outcome = ExtractService(rules=[RULE]).extract(_event(text))
        assert (outcome.signal is None) != (outcome.unrecognized is None)


def test_first_matching_rule_wins():
    never = ParserRule(
        rule_id="never",
        patterns=[r"(?P<symbol>ZZZ)\s+(?P<side>long)"],
        field_map={"symbol": "symbol", "side": "side"},
        side_aliases={"long": "LONG"},
    )
    outcome = ExtractService(rules=[never, RULE]).extract(_event("BTC long"))
    assert outcome.signal is not None
    assert outcome.signal.rule_id == "r1"
