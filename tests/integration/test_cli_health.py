from typer.testing import CliRunner

from verasig.cli import app

runner = CliRunner()


def test_health_reports_ok(monkeypatch, pg_url):
    monkeypatch.setenv("VERASIG_DATABASE_URL", pg_url)
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert "OK: db connected" in result.output
