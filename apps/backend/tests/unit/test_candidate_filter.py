from datetime import datetime, timezone

import pytest
from fakes import FakeExchange

from verasig.domain.event import MatchReason, MaterializationPath
from verasig.domain.message import RawTelegramMessage
from verasig.services.ingestion.candidate_filter import seed_candidate

D = MatchReason.DIRECTIONAL_KEYWORD
S = MatchReason.SYMBOL_TOKEN
P = MatchReason.PRICE_SHAPED

_EXCHANGE = FakeExchange({"BTC", "ETH", "SOL"})


def _instant() -> datetime:
    return datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)


def _msg(text: str | None, *, has_media: bool = False) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=7,
        message_id=42,
        text=text,
        posted_at=_instant(),
        captured_at=_instant(),
        has_media=has_media,
        raw_payload={},
    )


# (text, expected matched_reasons in canonical order); [] means rejected (None)
CASES = [
    ("gm frens wagmi", []),
    ("good morning, when is the next pump?", []),
    ("всем доброе утро, когда памп?", []),
    ("going long here, feeling good", [D]),
    ("продал половину позиции в плюс", [D]),
    ("$BTC looking strong today", [S]),
    ("entry 65000 sl 64000 tp 67000", [P]),
    ("🎯 67000 🛑 64000", [P]),
    ("BTC long entry 65k sl 64k tp 67k", [D, S, P]),
    ("зашёл в лонг по соляне, стоп под лоем", [D, P]),
]


@pytest.mark.parametrize("text,reasons", CASES)
def test_seed_candidate_matches_expected_reasons(text, reasons):
    event = seed_candidate(_msg(text), _EXCHANGE)
    if not reasons:
        assert event is None
        return
    assert event is not None
    assert event.matched_reasons == reasons
    assert event.materialized_by is MaterializationPath.SEED_HEURISTIC
    assert event.candidate_text == text
    assert (event.channel_id, event.message_id) == (7, 42)


def test_seed_candidate_rejects_media_only_message():
    assert seed_candidate(_msg(None, has_media=True), _EXCHANGE) is None


def test_seed_candidate_rejects_blank_text():
    assert seed_candidate(_msg("   \n  "), _EXCHANGE) is None


def test_seed_candidate_over_includes_chatter_that_mentions_a_symbol():
    # recall-first: a question about a listed symbol is still flagged (FP acceptable)
    event = seed_candidate(_msg("is BTC going to pump soon?"), _EXCHANGE)
    assert event is not None
    assert event.matched_reasons == [S]


def test_seed_candidate_carries_no_filter_rule_id():
    event = seed_candidate(_msg("BTC long"), _EXCHANGE)
    assert event.filter_rule_id is None
