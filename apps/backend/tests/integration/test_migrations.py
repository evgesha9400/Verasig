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


def test_multi_tenant_api_tables_and_columns_exist_after_upgrade(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")

    inspector = inspect(create_engine(pg_url, future=True))
    tables = set(inspector.get_table_names())
    assert {
        "user_account",
        "user_telegram_link",
        "user_channel",
        "user_exchange_connection",
        "chat_risk_config",
        "backtest_result",
        "lifecycle_link",
    } <= tables

    columns_by_table = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in (
            "golden_label",
            "filter_rule",
            "parser_rule",
            "extracted_signal",
            "unrecognized_signal",
            "parser_drift_warning",
            "filter_drift_warning",
        )
    }
    assert {"user_id", "label"} <= columns_by_table["golden_label"]
    assert "is_signal" not in columns_by_table["golden_label"]
    assert {"user_id", "display"} <= columns_by_table["filter_rule"]
    assert {"user_id"} <= columns_by_table["parser_rule"]
    assert {"user_id"} <= columns_by_table["extracted_signal"]
    assert {"user_id"} <= columns_by_table["unrecognized_signal"]
    assert {"user_id"} <= columns_by_table["parser_drift_warning"]
    assert {"user_id"} <= columns_by_table["filter_drift_warning"]
