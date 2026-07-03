from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_migrations_apply(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")  # no error == migrations apply


def test_feed_capture_tables_exist_after_upgrade(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")
    tables = set(inspect(create_engine(pg_url, future=True)).get_table_names())
    assert {"feed", "raw_message"} <= tables


def test_multi_tenant_api_tables_and_columns_exist_after_upgrade(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")

    inspector = inspect(create_engine(pg_url, future=True))
    tables = set(inspector.get_table_names())
    assert {
        "user_account",
        "source",
        "feed",
        "backfill_job_run",
        "user_exchange_connection",
        "feed_risk_config",
        "backtest_result",
        "lifecycle_link",
    } <= tables
    assert "user_telegram_link" not in tables

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
        "external_id",
        "status",
        "started_at",
        "finished_at",
        "fetched_count",
        "oldest_posted_at",
        "cursor_external_message_id",
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
            "feed_risk_config",
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
        "ck_feed_risk_config_entry_mode",
        "ck_feed_risk_config_weighting",
        "ck_feed_risk_config_exit_source",
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


def test_generic_source_replaces_telegram_link_after_upgrade(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")

    inspector = inspect(create_engine(pg_url, future=True))
    tables = set(inspector.get_table_names())
    assert "source" in tables
    assert "user_telegram_link" not in tables

    source_columns = {column["name"] for column in inspector.get_columns("source")}
    assert {
        "id",
        "user_id",
        "name",
        "status",
        "config_encrypted",
        "created_at",
        "updated_at",
    } <= source_columns

    source_checks = {
        check["name"] for check in inspector.get_check_constraints("source")
    }
    assert "ck_source_name" in source_checks

    source_uniques = {
        tuple(unique["column_names"])
        for unique in inspector.get_unique_constraints("source")
    }
    assert ("user_id", "name") in source_uniques


def test_feed_source_id_cascades_from_source_after_upgrade(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")

    inspector = inspect(create_engine(pg_url, future=True))
    feed_columns = {column["name"]: column for column in inspector.get_columns("feed")}
    assert "source_id" in feed_columns
    assert feed_columns["source_id"]["nullable"] is False

    source_fk = next(
        fk
        for fk in inspector.get_foreign_keys("feed")
        if fk["constrained_columns"] == ["source_id"]
    )
    assert source_fk["referred_table"] == "source"
    assert source_fk["options"].get("ondelete") == "CASCADE"


# Every table that owns a single-column user_id -> user_account FK. Deleting an
# account must cascade to purge that user's rows (models declare ondelete=CASCADE).
_USER_ACCOUNT_FK_TABLES = (
    "backfill_job_run",
    "backtest_result",
    "extracted_signal",
    "feed",
    "feed_risk_config",
    "filter_drift_warning",
    "filter_rule",
    "golden_label",
    "lifecycle_link",
    "parser_drift_warning",
    "parser_rule",
    "unrecognized_signal",
)

# Retired lab-benchmark tables (archive/lab-benchmark-runs); superseded by
# template mining (ADR 0013). They must never reappear in the migrated schema.
_RETIRED_LAB_TABLES = {
    "lab_benchmark_run",
    "lab_extraction_truth",
    "lab_model_run",
    "lab_prediction",
    "lab_provider_credential",
    "lab_review_event",
}


def test_no_model_migration_drift_after_upgrade(pg_url):
    """The migrated schema matches the ORM models: `alembic check` finds nothing."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")
    command.check(cfg)  # raises AutogenerateDiffsDetected on any model<->DB drift


def test_user_account_fks_cascade_after_upgrade(pg_url):
    """Each user_id -> user_account FK deletes its rows when the account is removed."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")

    inspector = inspect(create_engine(pg_url, future=True))
    not_cascading = {
        table
        for table in _USER_ACCOUNT_FK_TABLES
        for fk in inspector.get_foreign_keys(table)
        if fk["constrained_columns"] == ["user_id"]
        and fk["referred_table"] == "user_account"
        and fk["options"].get("ondelete") != "CASCADE"
    }
    assert not_cascading == set()


def test_retired_lab_tables_absent_after_upgrade(pg_url):
    """The archived lab-benchmark tables are not created by the migration chain."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")
    tables = set(inspect(create_engine(pg_url, future=True)).get_table_names())
    assert tables.isdisjoint(_RETIRED_LAB_TABLES)
