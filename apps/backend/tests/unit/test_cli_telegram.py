from datetime import datetime, timezone

import pytest
from typer.testing import CliRunner

from verasig.cli import app, format_stats
from verasig.domain.channel import TelegramChannel
from verasig.foundation.telethon_source import ChannelReferenceResolutionError

runner = CliRunner()


def _channel(**overrides) -> TelegramChannel:
    base = {
        "channel_id": 7,
        "title": "Pilot",
        "is_private": False,
        "first_seen_at": datetime(2026, 6, 3, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return TelegramChannel(**base)


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path, monkeypatch):
    # run in a temp CWD so the developer's real .env is never read by Settings
    monkeypatch.chdir(tmp_path)
    for var in (
        "VERASIG_TELEGRAM_API_ID",
        "VERASIG_TELEGRAM_API_HASH",
        "VERASIG_TELEGRAM_PHONE",
    ):
        monkeypatch.delenv(var, raising=False)


def test_whoami_without_credentials_exits_with_hint():
    result = runner.invoke(app, ["whoami"])
    assert result.exit_code == 1
    assert "VERASIG_TELEGRAM_API_ID" in result.stderr


def test_login_without_credentials_exits_with_hint():
    result = runner.invoke(app, ["login"])
    assert result.exit_code == 1
    assert "VERASIG_TELEGRAM_API_ID" in result.stderr


def test_whoami_without_session_exits_with_login_hint(tmp_path, monkeypatch):
    monkeypatch.setenv("VERASIG_TELEGRAM_API_ID", "1")
    monkeypatch.setenv("VERASIG_TELEGRAM_API_HASH", "abc")
    monkeypatch.setenv("VERASIG_SESSION_PATH", str(tmp_path / "absent.session"))
    result = runner.invoke(app, ["whoami"])
    assert result.exit_code == 1
    assert "run `login` first" in result.stderr


def test_backfill_without_credentials_exits_with_hint():
    result = runner.invoke(app, ["backfill", "@pilot"])
    assert result.exit_code == 1
    assert "VERASIG_TELEGRAM_API_ID" in result.stderr


def test_backfill_reference_error_exits_without_traceback(monkeypatch):
    async def fail_backfill(*_args):
        raise ChannelReferenceResolutionError("No joined dialog has title 'Missing'")

    monkeypatch.setattr("verasig.cli.make_client", lambda settings: object())
    monkeypatch.setattr("verasig.cli._connected_backfill", fail_backfill)

    result = runner.invoke(app, ["backfill", "title:Missing"])

    assert result.exit_code == 1
    assert "No joined dialog has title 'Missing'" in result.stderr
    assert "Traceback" not in result.stderr


def test_format_stats_renders_handle_cursor_and_subs():
    channel = _channel(
        handle="pilot", subscriber_count=100, captured_through_message_id=42
    )
    assert (
        format_stats(channel, 30)
        == "Pilot · @pilot · id=7 · captured=30 · cursor=42 · subs=100"
    )


def test_format_stats_omits_handle_subs_and_marks_empty_cursor():
    channel = _channel(title="Private", is_private=True)
    assert format_stats(channel, 0) == "Private · id=7 · captured=0 · cursor=none"
