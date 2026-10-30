from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


def test_migrations_apply(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")  # no error == migrations apply


def test_mining_review_schema_exists_after_upgrade(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")

    inspector = inspect(create_engine(pg_url, future=True))
    tables = set(inspector.get_table_names())
    assert "mine_result" not in tables
    assert "mining_review" in tables
    feed_columns = {column["name"] for column in inspector.get_columns("feed")}
    assert "capture_generation" in feed_columns
    review_columns = {
        column["name"] for column in inspector.get_columns("mining_review")
    }
    assert {
        "id",
        "user_id",
        "external_id",
        "input_revision",
        "payload",
        "overlay",
        "accepted_template_keys",
        "missed_message_ids",
        "confirmed_at",
        "created_at",
    } <= review_columns


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
        "mining_review",
    } <= tables
    assert "user_telegram_link" not in tables

    signal_columns = {column["name"] for column in inspector.get_columns("signal")}
    assert {"user_id"} <= signal_columns

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
        "signal",
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
            "signal",
            "deleted_signal_evidence",
            "backfill_job_run",
            "mining_review",
        )
        for index in inspector.get_indexes(table)
    }
    assert {
        "ix_backtest_result_user_channel_completed",
        "ix_signal_user_channel",
        "ix_deleted_signal_evidence_channel",
        "ix_backfill_job_run_user_channel_started",
        "ix_backfill_job_run_status",
        "ix_mining_review_feed_created",
    } <= index_names

    check_names = {
        check["name"]
        for table in (
            "signal",
            "deleted_signal_evidence",
            "backfill_job_run",
            "feed_risk_config",
        )
        for check in inspector.get_check_constraints(table)
    }
    assert {
        "ck_signal_side",
        "ck_signal_event_type",
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
            "signal",
            "lifecycle_link",
        )
        for foreign_key in inspector.get_foreign_keys(table)
    }
    assert {
        "fk_signal_message",
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
    "signal",
    "feed",
    "feed_risk_config",
    "lifecycle_link",
    "mining_review",
    "user_exchange_connection",
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


def test_signal_table_exists_without_legacy_event_tables(pg_url):
    """The current schema has one `signal` table — no separate event/extraction
    tables from the pre-squash pipeline this repo no longer runs."""
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")

    tables = set(inspect(create_engine(pg_url, future=True)).get_table_names())
    assert "signal" in tables
    assert "raw_signal_event" not in tables
    assert "extracted_signal" not in tables


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


@pytest.fixture
def fresh_db_url(pg_url):
    """An empty database in the shared container, for stepping through revisions."""
    name = f"migrate_{uuid4().hex[:12]}"
    admin = create_engine(pg_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f"CREATE DATABASE {name}"))
    yield make_url(pg_url).set(database=name).render_as_string(hide_password=False)
    with admin.connect() as connection:
        connection.execute(text(f"DROP DATABASE {name} WITH (FORCE)"))
    admin.dispose()


def _insert_account(
    connection, email: str, plan: str, cancel_at: datetime | None = None
) -> None:
    connection.execute(
        text(
            """
            INSERT INTO user_account
                (id, email, password_hash, first_name, last_name, plan, cancel_at,
                 created_at)
            VALUES (:id, :email, 'hash', 'Ada', 'Lovelace', :plan, :cancel_at, :now)
            """
        ),
        {
            "id": uuid4(),
            "email": email,
            "plan": plan,
            "cancel_at": cancel_at,
            "now": datetime.now(tz=UTC),
        },
    )


def test_billing_migration_remaps_old_plans_and_adds_billing_columns(fresh_db_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", fresh_db_url.replace("%", "%%"))
    command.upgrade(cfg, "0001_init")
    engine = create_engine(fresh_db_url, future=True)
    with engine.begin() as connection:
        _insert_account(connection, "observer@example.com", "observer")
        # the removed fake cancel flow wrote cancel_at without any subscription
        _insert_account(
            connection, "operator@example.com", "operator", datetime.now(tz=UTC)
        )
        _insert_account(connection, "desk@example.com", "desk")

    command.upgrade(cfg, "head")

    with engine.connect() as connection:
        plans = dict(
            connection.execute(text("SELECT email, plan FROM user_account")).all()
        )
        cancel_ats = connection.execute(
            text("SELECT count(*) FROM user_account WHERE cancel_at IS NOT NULL")
        ).scalar_one()
    columns = {column["name"] for column in inspect(engine).get_columns("user_account")}
    engine.dispose()
    assert plans == {
        "observer@example.com": "free",
        "operator@example.com": "trader",
        "desk@example.com": "desk",
    }
    assert cancel_ats == 0
    assert {
        "stripe_customer_id",
        "stripe_subscription_id",
        "subscription_status",
        "cancel_at",
    } <= columns


def test_billing_migration_rejects_old_plan_names_and_defaults_to_free(fresh_db_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", fresh_db_url.replace("%", "%%"))
    command.upgrade(cfg, "head")
    engine = create_engine(fresh_db_url, future=True)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO user_account
                    (id, email, password_hash, first_name, last_name, created_at)
                VALUES (:id, 'default@example.com', 'hash', 'Ada', 'Lovelace', now())
                """
            ),
            {"id": uuid4()},
        )
        default_plan = connection.execute(
            text("SELECT plan FROM user_account WHERE email = 'default@example.com'")
        ).scalar_one()
    with pytest.raises(Exception, match="ck_user_account_plan"):
        with engine.begin() as connection:
            _insert_account(connection, "old@example.com", "observer")
    engine.dispose()
    assert default_plan == "free"


def test_billing_migration_downgrades_back_to_the_old_plan_names(fresh_db_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", fresh_db_url.replace("%", "%%"))
    command.upgrade(cfg, "head")
    engine = create_engine(fresh_db_url, future=True)
    with engine.begin() as connection:
        _insert_account(connection, "free@example.com", "free")
        _insert_account(connection, "trader@example.com", "trader")

    command.downgrade(cfg, "0001_init")

    with engine.connect() as connection:
        plans = dict(
            connection.execute(text("SELECT email, plan FROM user_account")).all()
        )
    engine.dispose()
    assert plans == {
        "free@example.com": "observer",
        "trader@example.com": "operator",
    }
