from datetime import datetime, timezone

from fakes import FakeExchange

from verasig.domain.channel import TelegramChannel
from verasig.domain.drift import MissDiscoveredBy
from verasig.domain.event import MaterializationPath
from verasig.domain.filter_rule import FilterRule
from verasig.domain.message import RawTelegramMessage
from verasig.domain.parser_rule import ParserRule
from verasig.foundation.static_exchange import StaticExchange
from verasig.services.ingestion.candidate_derivation import (
    derive_candidates,
    sweep_advisory,
)
from verasig.storage import repositories as repo

_LONG_RULE = ParserRule(
    rule_id="long",
    patterns=[r"(?i)(?P<symbol>[A-Z]{2,10})\s+(?P<side>long|short|buy|sell)"],
    field_map={"symbol": "symbol", "side": "side"},
    side_aliases={"long": "LONG", "short": "SHORT", "buy": "LONG", "sell": "SHORT"},
)
# provider slang the generic seed does not know: "pump"/"dump" as direction
_SLANG_RULE = ParserRule(
    rule_id="slang",
    patterns=[r"(?i)(?P<symbol>[A-Z]{2,10})\s+(?P<side>pump|dump)"],
    field_map={"symbol": "symbol", "side": "side"},
    side_aliases={"pump": "LONG", "dump": "SHORT"},
)


def _instant() -> datetime:
    return datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)


def _seed(session_factory, texts: dict[int, str]) -> None:
    with session_factory() as session:
        repo.upsert_channel(
            session,
            TelegramChannel(
                channel_id=7,
                handle="pilot",
                title="Pilot",
                is_private=False,
                first_seen_at=_instant(),
            ),
        )
        repo.insert_messages(
            session,
            [
                RawTelegramMessage(
                    channel_id=7,
                    message_id=mid,
                    text=text,
                    posted_at=_instant(),
                    captured_at=_instant(),
                    has_media=False,
                    raw_payload={"id": mid},
                )
                for mid, text in texts.items()
            ],
        )
        session.commit()


# message 1: a normal signal (seed flags); 2: chatter; 3: a seed-miss the slang
# parser still recovers (ZZZ unlisted, "pump" not a seed directional keyword)
_CORPUS = {
    1: "BTC long entry 65k sl 64k tp 67k",
    2: "gm frens, lovely day",
    3: "ZZZ pump now friends",
}


def test_derive_flags_signals_as_seed_heuristic_not_chatter(session_factory):
    _seed(session_factory, _CORPUS)
    created = derive_candidates(session_factory, 7, FakeExchange({"BTC"}))
    assert created == 1
    with session_factory() as session:
        events = repo.read_signal_events(session, 7)
    assert {e.message_id for e in events} == {1}
    assert events[0].materialized_by is MaterializationPath.SEED_HEURISTIC


def test_derive_is_idempotent(session_factory):
    _seed(session_factory, _CORPUS)
    derive_candidates(session_factory, 7, FakeExchange({"BTC"}))
    again = derive_candidates(session_factory, 7, FakeExchange({"BTC"}))
    assert again == 0


def test_derive_uses_distilled_filter_rule_over_seed(session_factory):
    _seed(session_factory, {9: "alpha leak incoming"})  # seed alone would miss this
    rule = FilterRule(
        rule_id="7-filter-v1", channel_id=7, include_patterns=[r"(?i)alpha leak"]
    )
    with session_factory() as session:
        repo.upsert_filter_rule(session, rule)
        session.commit()
    created = derive_candidates(session_factory, 7, StaticExchange())
    assert created == 1
    with session_factory() as session:
        event = repo.read_signal_events(session, 7)[0]
    assert event.materialized_by is MaterializationPath.FILTER_RULE
    assert event.filter_rule_id == "7-filter-v1"


def test_sweep_recovers_filter_miss_with_one_drift(session_factory):
    _seed(session_factory, _CORPUS)
    derive_candidates(session_factory, 7, FakeExchange({"BTC"}))  # candidates = {1}
    new_events, new_drift = sweep_advisory(
        session_factory, 7, [_LONG_RULE, _SLANG_RULE]
    )
    assert (new_events, new_drift) == (1, 1)  # only message 3 (a true miss)
    with session_factory() as session:
        events = {e.message_id: e for e in repo.read_signal_events(session, 7)}
        warnings = repo.read_drift_warnings(session, 7)
    assert events[3].materialized_by is MaterializationPath.PARSER_BACKFILL
    assert len(warnings) == 1
    assert warnings[0].message_id == 3
    assert warnings[0].miss_discovered_by is MissDiscoveredBy.PARSER_BACKFILL
    assert warnings[0].event_id == events[3].id


def test_sweep_does_not_drift_on_existing_candidate(session_factory):
    _seed(session_factory, _CORPUS)
    derive_candidates(session_factory, 7, FakeExchange({"BTC"}))
    # message 1 is already a candidate AND parses via _LONG_RULE -> must NOT drift
    sweep_advisory(session_factory, 7, [_LONG_RULE, _SLANG_RULE])
    with session_factory() as session:
        warnings = repo.read_drift_warnings(session, 7)
    assert all(w.message_id != 1 for w in warnings)


def test_sweep_is_idempotent(session_factory):
    _seed(session_factory, _CORPUS)
    derive_candidates(session_factory, 7, FakeExchange({"BTC"}))
    sweep_advisory(session_factory, 7, [_SLANG_RULE])
    again = sweep_advisory(session_factory, 7, [_SLANG_RULE])
    assert again == (0, 0)
