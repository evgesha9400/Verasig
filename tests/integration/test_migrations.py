from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


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
