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
        "backfill_job_run",
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

    backfill_columns = {
        column["name"] for column in inspector.get_columns("backfill_job_run")
    }
    assert {
        "id",
        "user_id",
        "channel_id",
        "status",
        "started_at",
        "finished_at",
        "fetched_count",
        "oldest_posted_at",
        "cursor_message_id",
        "error_code",
        "error_message",
    } <= backfill_columns


def test_schema_hardening_constraints_exist_after_upgrade(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")

    inspector = inspect(create_engine(pg_url, future=True))

    required_user_tables = {
        "golden_label",
        "filter_rule",
        "parser_rule",
        "extracted_signal",
        "unrecognized_signal",
        "parser_drift_warning",
        "filter_drift_warning",
    }
    nullable_user_tables = {
        table
        for table in required_user_tables
        for column in inspector.get_columns(table)
        if column["name"] == "user_id" and column["nullable"]
    }
    assert nullable_user_tables == set()

    index_names = {
        index["name"]
        for table in (
            "backtest_result",
            "extracted_signal",
            "unrecognized_signal",
            "parser_rule",
            "filter_rule",
            "deleted_signal_evidence",
            "backfill_job_run",
            "parser_drift_warning",
            "filter_drift_warning",
        )
        for index in inspector.get_indexes(table)
    }
    assert {
        "ix_backtest_result_user_channel_completed",
        "ix_extracted_signal_user_channel",
        "ix_unrecognized_signal_user_event",
        "ix_parser_rule_user_channel",
        "ix_filter_rule_user_channel",
        "ix_deleted_signal_evidence_channel",
        "ix_backfill_job_run_user_channel_started",
        "ix_backfill_job_run_status",
        "ix_parser_drift_warning_user_channel",
        "ix_filter_drift_warning_user_channel",
    } <= index_names

    check_names = {
        check["name"]
        for table in (
            "golden_label",
            "extracted_signal",
            "deleted_signal_evidence",
            "backfill_job_run",
            "chat_risk_config",
        )
        for check in inspector.get_check_constraints(table)
    }
    assert {
        "ck_golden_label_label",
        "ck_extracted_signal_side",
        "ck_extracted_signal_event_type",
        "ck_extracted_signal_extraction_method",
        "ck_deleted_signal_evidence_confidence",
        "ck_deleted_signal_evidence_method",
        "ck_backfill_job_run_status",
        "ck_chat_risk_config_entry_mode",
        "ck_chat_risk_config_weighting",
        "ck_chat_risk_config_exit_source",
    } <= check_names

    foreign_key_names = {
        foreign_key["name"]
        for table in (
            "raw_signal_event",
            "golden_label",
            "filter_drift_warning",
            "lifecycle_link",
        )
        for foreign_key in inspector.get_foreign_keys(table)
    }
    assert {
        "fk_raw_signal_event_message",
        "fk_golden_label_message",
        "fk_filter_drift_warning_message",
        "fk_lifecycle_link_root_signal",
    } <= foreign_key_names
