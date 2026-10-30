"""Miner Candidate -> domain mapping (mining_signals).

Pure unit tests over the single translation site: a miner Candidate's structured
fields become a Signal. Candidates are built directly (not via the miner) so the
mapping is tested in isolation from extraction.
"""

from decimal import Decimal

from verasig.domain.signal import EntryType, Side
from verasig.features.mining.mining_signals import candidate_to_signal
from verasig.features.mining.template_mining.fields import SignalEntry, StructuredFields
from verasig.features.mining.template_mining.types import Candidate, ChatMessage


def _candidate(fields: StructuredFields, *, confidence: float = 0.8) -> Candidate:
    return Candidate(
        message=ChatMessage(id="42", text="raw text"),
        instruments=[],
        directions=[],
        prices=[],
        fields=fields,
        intent="new_signal",
        confidence=confidence,
        rejection_reasons=[],
        parser_issues=[],
        template_key="tpl_abc",
        normalized_template="INSTRUMENT DIRECTION",
    )


def _fields(**overrides) -> StructuredFields:
    base = {"instrument": "BTCUSDT", "direction": "BUY"}
    return StructuredFields(**{**base, **overrides})


def test_maps_single_entry_to_limit_single():
    entry = SignalEntry(type="single", price=100.5)
    fields = _fields(entry=entry, stop_loss=95.0, take_profits=[110.0, 120.0])

    signal = candidate_to_signal(_candidate(fields), 7, "tpl_abc")

    assert signal.symbol == "BTCUSDT"
    assert signal.side is Side.LONG
    assert signal.entry_type is EntryType.LIMIT_SINGLE
    assert signal.entry_low == Decimal("100.5")
    assert signal.entry_high == Decimal("100.5")
    assert signal.stop_loss == Decimal("95")
    assert signal.take_profits == [Decimal("110"), Decimal("120")]
    assert signal.channel_id == 7
    assert signal.message_id == 42
    assert signal.candidate_text == "raw text"
    assert signal.rule_id == "tpl_abc"


def test_rule_id_is_the_claiming_family_not_the_candidates_own_key():
    # A fallback match persists the general accepted family's key.
    signal = candidate_to_signal(_candidate(_fields()), 7, "tpl_general")

    assert signal.rule_id == "tpl_general"


def test_maps_leverage_onto_the_signal():
    signal = candidate_to_signal(_candidate(_fields(leverage=10.0)), 7, "tpl_abc")

    assert signal.leverage == Decimal("10.0")


def test_maps_range_entry_to_limit_range():
    entry = SignalEntry(type="range", min=200.0, max=210.0)
    fields = _fields(direction="SELL", entry=entry)

    signal = candidate_to_signal(_candidate(fields), 7, "tpl_abc")

    assert signal.side is Side.SHORT
    assert signal.entry_type is EntryType.LIMIT_RANGE
    assert signal.entry_low == Decimal("200")
    assert signal.entry_high == Decimal("210")


def test_maps_market_entry_to_market():
    fields = _fields(entry=SignalEntry(type="market"))

    signal = candidate_to_signal(_candidate(fields), 7, "tpl_abc")

    assert signal.entry_type is EntryType.MARKET
    assert signal.entry_low is None
    assert signal.entry_high is None


def test_missing_entry_defaults_to_market():
    fields = _fields(entry=None)

    signal = candidate_to_signal(_candidate(fields), 7, "tpl_abc")

    assert signal.entry_type is EntryType.MARKET


def test_carries_confidence_as_decimal():
    signal = candidate_to_signal(_candidate(_fields(), confidence=0.625), 7, "tpl_abc")

    assert signal.confidence == Decimal("0.625")


def test_candidate_without_instrument_is_not_persistable():
    fields = _fields(instrument=None)

    assert candidate_to_signal(_candidate(fields), 7, "tpl_abc") is None


def test_candidate_without_direction_is_not_persistable():
    fields = _fields(direction=None)

    assert candidate_to_signal(_candidate(fields), 7, "tpl_abc") is None
