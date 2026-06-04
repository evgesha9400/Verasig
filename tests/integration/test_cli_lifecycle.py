from datetime import datetime, timedelta, timezone
from uuid import UUID

from typer.testing import CliRunner

from verasig.cli import app
from verasig.domain.channel import TelegramChannel
from verasig.domain.event import MaterializationPath, RawSignalEvent
from verasig.domain.message import RawTelegramMessage
from verasig.domain.signal import EntryType, ExtractedSignal, Side
from verasig.storage import repositories as repo

runner = CliRunner()

_ROOT = UUID("3f2a0000-0000-0000-0000-000000000000")
_EVENT = UUID("0e0e0e0e-0000-0000-0000-000000000000")
_BASE = datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc)


def _at(minutes: int) -> datetime:
    return _BASE + timedelta(minutes=minutes)


def _message(message_id: int, minutes: int, text: str, reply_to=None):
    return RawTelegramMessage(
        channel_id=7,
        message_id=message_id,
        text=text,
        posted_at=_at(minutes),
        captured_at=_at(minutes),
        reply_to_message_id=reply_to,
        has_media=False,
        raw_payload={"id": message_id},
    )


def _seed_lifecycle(session_factory) -> None:
    with session_factory() as session:
        repo.upsert_channel(
            session,
            TelegramChannel(
                channel_id=7,
                handle="pilot",
                title="Pilot",
                is_private=False,
                first_seen_at=_at(0),
            ),
        )
        repo.insert_messages(
            session,
            [
                _message(1, 0, "BTC long entry 65000 sl 64000 tp 67000"),
                _message(2, 30, "add at 63000", reply_to=1),
                _message(3, 70, "closed", reply_to=1),
            ],
        )
        repo.insert_signal_events(
            session,
            [
                RawSignalEvent(
                    id=_EVENT,
                    channel_id=7,
                    message_id=1,
                    candidate_text="BTC long entry 65000 sl 64000 tp 67000",
                    materialized_by=MaterializationPath.SEED_HEURISTIC,
                )
            ],
        )
        repo.insert_extracted_signals(
            session,
            [
                ExtractedSignal(
                    id=_ROOT,
                    event_id=_EVENT,
                    channel_id=7,
                    symbol="BTC",
                    side=Side.LONG,
                    entry_type=EntryType.LIMIT_SINGLE,
                    entry_low="65000",
                    stop_loss="64000",
                    take_profits=["67000"],
                )
            ],
        )
        session.commit()


def test_lifecycle_cli_prints_folded_timeline(session_factory, monkeypatch, pg_url):
    _seed_lifecycle(session_factory)
    monkeypatch.setenv("VERASIG_DATABASE_URL", pg_url)
    result = runner.invoke(app, ["lifecycle", "@pilot"])
    assert result.exit_code == 0
    output = result.output
    assert "BTCUSDT LONG" in output
    assert "root=3f2a0000" in output
    assert "steps=3" in output
    assert "NEW_ENTRY" in output
    assert "MODIFY" in output and "(add)" in output
    assert "size=2" in output  # after the priced average-in
    assert "entry=64000" in output  # size-weighted entry
    assert "CLOSE" in output
    assert "closed=2026-06-04T13:10Z" in output


def test_lifecycle_cli_unknown_channel_exits_nonzero(monkeypatch, pg_url):
    monkeypatch.setenv("VERASIG_DATABASE_URL", pg_url)
    result = runner.invoke(app, ["lifecycle", "@ghost"])
    assert result.exit_code == 1
