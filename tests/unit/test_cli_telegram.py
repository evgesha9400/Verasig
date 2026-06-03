import pytest
from typer.testing import CliRunner

from verasig.cli import app

runner = CliRunner()


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
