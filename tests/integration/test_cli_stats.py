from datetime import datetime, timezone

from typer.testing import CliRunner

from verasig.cli import app
from verasig.domain.channel import TelegramChannel
from verasig.domain.message import RawTelegramMessage
from verasig.storage import repositories as repo

runner = CliRunner()


def _instant() -> datetime:
    return datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)


def _message(message_id: int) -> RawTelegramMessage:
    return RawTelegramMessage(
        channel_id=7,
        message_id=message_id,
        posted_at=_instant(),
        captured_at=_instant(),
        has_media=False,
        raw_payload={"id": message_id},
    )


def _populate(session_factory) -> None:
    with session_factory() as session:
        repo.upsert_channel(
            session,
            TelegramChannel(
                channel_id=7,
                handle="pilot",
                title="Pilot",
                is_private=False,
                first_seen_at=_instant(),
                subscriber_count=100,
            ),
        )
        repo.insert_messages(session, [_message(1), _message(2), _message(3)])
        repo.advance_cursor(session, 7, 3)
        session.commit()


def test_stats_prints_capture_count_and_cursor(session_factory, monkeypatch, pg_url):
    _populate(session_factory)
    monkeypatch.setenv("VERASIG_DATABASE_URL_OVERRIDE", pg_url)
    result = runner.invoke(app, ["stats", "@pilot"])
    assert result.exit_code == 0
    assert "id=7" in result.output
    assert "captured=3" in result.output
    assert "cursor=3" in result.output


def test_stats_resolves_by_numeric_id(session_factory, monkeypatch, pg_url):
    _populate(session_factory)
    monkeypatch.setenv("VERASIG_DATABASE_URL_OVERRIDE", pg_url)
    result = runner.invoke(app, ["stats", "7"])
    assert result.exit_code == 0
    assert "captured=3" in result.output


def test_stats_resolves_by_exact_title(session_factory, monkeypatch, pg_url):
    _populate(session_factory)
    monkeypatch.setenv("VERASIG_DATABASE_URL_OVERRIDE", pg_url)
    result = runner.invoke(app, ["stats", "title:Pilot"])
    assert result.exit_code == 0
    assert "captured=3" in result.output


def test_stats_unknown_channel_exits_nonzero(session_factory, monkeypatch, pg_url):
    monkeypatch.setenv("VERASIG_DATABASE_URL_OVERRIDE", pg_url)
    result = runner.invoke(app, ["stats", "@ghost"])
    assert result.exit_code == 1
