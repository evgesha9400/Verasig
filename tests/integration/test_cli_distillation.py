from datetime import datetime, timezone

from fakes import FakeExtractor
from typer.testing import CliRunner

from verasig.cli import app
from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage
from verasig.domain.parser_rule import ParserRule
from verasig.domain.signal import Side, TradeIntent
from verasig.storage import repositories as repo

runner = CliRunner()

_LONG_RULE = ParserRule(
    rule_id="7-parser-1-v1",
    channel_id=7,
    patterns=[
        r"(?i)(?P<symbol>[A-Z]{2,10})\s+(?P<side>long|short|buy|sell)"
        r"(?:.*?entry[:\s]+(?P<entry>[\d.,]+k?))?"
    ],
    field_map={"symbol": "symbol", "side": "side", "entry": "entry"},
    side_aliases={"long": "LONG", "short": "SHORT", "buy": "LONG", "sell": "SHORT"},
)
_SLANG_RULE = ParserRule(
    rule_id="7-parser-2-v1",
    channel_id=7,
    patterns=[r"(?i)(?P<symbol>[A-Z]{2,10})\s+(?P<side>pump|dump)"],
    field_map={"symbol": "symbol", "side": "side"},
    side_aliases={"pump": "LONG", "dump": "SHORT"},
)


def _instant() -> datetime:
    return datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)


def _populate(session_factory) -> None:
    texts = {
        1: "BTC long entry 65000 sl 64000 tp 67000",
        2: "gm frens lovely day",
        3: "ZZZ pump now friends",
    }
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


def _add_rule(session_factory, rule) -> None:
    with session_factory() as session:
        repo.upsert_parser_rules(session, [rule])
        session.commit()


def test_candidates_cli_derives_seed_events(session_factory, monkeypatch, pg_url):
    _populate(session_factory)
    monkeypatch.setenv("VERASIG_DATABASE_URL", pg_url)
    result = runner.invoke(app, ["candidates", "@pilot"])
    assert result.exit_code == 0
    assert "+1 new" in result.output  # only the BTC long signal is seed-flagged
    with session_factory() as session:
        assert {e.message_id for e in repo.read_signal_events(session, 7)} == {1}


def test_extract_cli_produces_signals(session_factory, monkeypatch, pg_url):
    _populate(session_factory)
    _add_rule(session_factory, _LONG_RULE)
    monkeypatch.setenv("VERASIG_DATABASE_URL", pg_url)
    runner.invoke(app, ["candidates", "@pilot"])
    result = runner.invoke(app, ["extract", "@pilot", "--no-llm"])
    assert result.exit_code == 0
    assert "1 det" in result.output
    with session_factory() as session:
        assert len(repo.read_extracted_signals(session, 7)) == 1


def test_extract_cli_with_injected_fallback_emits_drift(
    session_factory, monkeypatch, pg_url
):
    _populate(session_factory)  # no parser rule → deterministic miss on the candidate
    monkeypatch.setenv("VERASIG_DATABASE_URL", pg_url)
    monkeypatch.setattr(
        "verasig.cli._make_fallback_extractor",
        lambda settings: FakeExtractor(
            returns=TradeIntent(symbol="BTC", side=Side.LONG)
        ),
    )
    runner.invoke(app, ["candidates", "@pilot"])
    result = runner.invoke(app, ["extract", "@pilot"])
    assert result.exit_code == 0
    assert "1 llm" in result.output
    assert "+1 parser-drift" in result.output
    with session_factory() as session:
        signals = repo.read_extracted_signals(session, 7)
        drifts = repo.read_parser_drift_warnings(session, 7)
    assert len(signals) == 1 and signals[0].extraction_method == "LLM_FALLBACK"
    assert len(drifts) == 1


def test_extract_cli_no_llm_yields_unrecognized(session_factory, monkeypatch, pg_url):
    _populate(session_factory)  # no parser rule, fallback disabled → unrecognized
    monkeypatch.setenv("VERASIG_DATABASE_URL", pg_url)
    runner.invoke(app, ["candidates", "@pilot"])
    result = runner.invoke(app, ["extract", "@pilot", "--no-llm"])
    assert result.exit_code == 0
    assert "1 unrecognized" in result.output
    assert "+0 parser-drift" in result.output
    with session_factory() as session:
        assert repo.read_extracted_signals(session, 7) == []
        assert len(repo.read_unrecognized_signals(session, 7)) == 1


def test_sweep_cli_recovers_filter_miss(session_factory, monkeypatch, pg_url):
    _populate(session_factory)
    _add_rule(session_factory, _SLANG_RULE)
    monkeypatch.setenv("VERASIG_DATABASE_URL", pg_url)
    runner.invoke(app, ["candidates", "@pilot"])  # candidates = {1}
    result = runner.invoke(app, ["sweep", "@pilot"])
    assert result.exit_code == 0
    assert "+1 recovered" in result.output
    assert "+1 drift" in result.output
    with session_factory() as session:
        assert len(repo.read_drift_warnings(session, 7)) == 1


def test_candidates_cli_unknown_channel_exits_nonzero(
    session_factory, monkeypatch, pg_url
):
    monkeypatch.setenv("VERASIG_DATABASE_URL", pg_url)
    result = runner.invoke(app, ["candidates", "@ghost"])
    assert result.exit_code == 1


def test_workbench_cli_launches_for_known_channel(session_factory, monkeypatch, pg_url):
    _populate(session_factory)
    monkeypatch.setenv("VERASIG_DATABASE_URL", pg_url)
    launched: list[int] = []
    monkeypatch.setattr("verasig.cli._launch_workbench", launched.append)
    result = runner.invoke(app, ["workbench", "@pilot"])
    assert result.exit_code == 0
    assert launched == [7]  # resolved channel id, no real Streamlit launched


def test_workbench_cli_unknown_channel_exits_nonzero(
    session_factory, monkeypatch, pg_url
):
    monkeypatch.setenv("VERASIG_DATABASE_URL", pg_url)
    result = runner.invoke(app, ["workbench", "@ghost"])
    assert result.exit_code == 1
