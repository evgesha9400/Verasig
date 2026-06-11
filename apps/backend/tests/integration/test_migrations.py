from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from typer.testing import CliRunner

from verasig.cli import app

runner = CliRunner()


def test_migrations_apply(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")  # no error == migrations apply


def test_raw_capture_tables_exist_after_upgrade(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")
    tables = set(inspect(create_engine(pg_url, future=True)).get_table_names())
    assert {"telegram_channel", "raw_telegram_message"} <= tables


def test_migrate_command_applies_head(pg_url, monkeypatch):
    monkeypatch.setenv("VERASIG_DATABASE_URL_OVERRIDE", pg_url)
    result = runner.invoke(app, ["migrate"])
    assert result.exit_code == 0
    tables = set(inspect(create_engine(pg_url, future=True)).get_table_names())
    assert {"telegram_channel", "raw_telegram_message"} <= tables
