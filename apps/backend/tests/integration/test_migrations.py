from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from testcontainers.postgres import PostgresContainer


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
            "extracted_signal",
            "unrecognized_signal",
        )
    }
    assert {"user_id"} <= columns_by_table["extracted_signal"]
    assert {"user_id"} <= columns_by_table["unrecognized_signal"]

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
        "extracted_signal",
        "unrecognized_signal",
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
            "deleted_signal_evidence",
            "backfill_job_run",
        )
        for index in inspector.get_indexes(table)
    }
    assert {
        "ix_backtest_result_user_channel_completed",
        "ix_extracted_signal_user_channel",
        "ix_unrecognized_signal_user_event",
        "ix_deleted_signal_evidence_channel",
        "ix_backfill_job_run_user_channel_started",
        "ix_backfill_job_run_status",
    } <= index_names

    check_names = {
        check["name"]
        for table in (
            "extracted_signal",
            "deleted_signal_evidence",
            "backfill_job_run",
            "feed_risk_config",
        )
        for check in inspector.get_check_constraints(table)
    }
    assert {
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
            "lifecycle_link",
        )
        for foreign_key in inspector.get_foreign_keys(table)
    }
    assert {
        "fk_raw_signal_event_message",
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
    "lifecycle_link",
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


# ── 0010 orphan purge (regression: purge must precede the raw_message PK) ──────

_USER_ID = "11111111-1111-1111-1111-111111111111"
_LEGIT_CHANNEL = 1001  # subscribed -> survives
_ORPHAN_CHANNEL = 2002  # no user_channel -> capture is orphaned -> purged

# (id-suffix, channel): one full capture graph per channel.
_CHANNELS = ((1, _LEGIT_CHANNEL), (2, _ORPHAN_CHANNEL))


def _seed_capture_graph(connection, id_suffix: int, channel: int) -> None:
    """Insert a full 0009 capture graph (message -> event -> derived rows)."""

    def uid(kind: str) -> str:
        return f"{id_suffix}{kind}000000-0000-0000-0000-000000000000"[:36]

    event_id, label_id = uid("e"), uid("a")
    connection.execute(
        text(
            "INSERT INTO telegram_channel "
            "(channel_id, title, is_private, first_seen_at) "
            "VALUES (:c, 't', false, now())"
        ),
        {"c": channel},
    )
    connection.execute(
        text(
            "INSERT INTO raw_telegram_message "
            "(channel_id, message_id, posted_at, captured_at, has_media, raw_payload) "
            "VALUES (:c, 10, now(), now(), false, '{}')"
        ),
        {"c": channel},
    )
    connection.execute(
        text(
            "INSERT INTO raw_signal_event "
            "(id, channel_id, message_id, candidate_text, materialized_by, "
            "matched_reasons, created_at) "
            "VALUES (:id, :c, 10, 'buy', 'filter', '[]', now())"
        ),
        {"id": event_id, "c": channel},
    )
    connection.execute(
        text(
            "INSERT INTO extracted_signal "
            "(id, event_id, channel_id, symbol, side, event_type, take_profits, "
            "extraction_method, extracted_at, user_id) "
            "VALUES (:id, :ev, :c, 'BTC', 'LONG', 'NEW_ENTRY', '[]', "
            "'DETERMINISTIC', now(), :u)"
        ),
        {"id": uid("b"), "ev": event_id, "c": channel, "u": _USER_ID},
    )
    connection.execute(
        text(
            "INSERT INTO golden_label "
            "(id, channel_id, message_id, labeled_at, user_id, label) "
            "VALUES (:id, :c, 10, now(), :u, 'signal')"
        ),
        {"id": label_id, "c": channel, "u": _USER_ID},
    )
    connection.execute(
        text(
            "INSERT INTO filter_drift_warning "
            "(id, channel_id, message_id, miss_discovered_by, event_id, "
            "source_label_id, created_at, user_id) "
            "VALUES (:id, :c, 10, 'test', :ev, :lbl, now(), :u)"
        ),
        {"id": uid("f"), "c": channel, "ev": event_id, "lbl": label_id, "u": _USER_ID},
    )
    connection.execute(
        text(
            "INSERT INTO deleted_signal_evidence "
            "(id, channel_id, message_id, confidence, method, detected_at, "
            "was_signal_candidate) "
            "VALUES (:id, :c, 10, 'CONFIRMED', 'ID_GAP', now(), true)"
        ),
        {"id": uid("d"), "c": channel},
    )


def test_0010_purges_orphan_capture_before_tightening_keys():
    """0010 must upgrade cleanly when orphan capture (no subscriber) exists, and
    purge it while preserving the subscribed channel's rows."""
    with PostgresContainer("postgres:16") as pg:
        url = pg.get_connection_url().replace("psycopg2", "psycopg")
        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", url)
        command.upgrade(cfg, "0009_backfill_job_runs")

        engine = create_engine(url, future=True)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO user_account "
                    "(id, email, password_hash, first_name, last_name, plan, "
                    "created_at) "
                    "VALUES (:u, 'a@b.co', 'h', 'A', 'B', 'observer', now())"
                ),
                {"u": _USER_ID},
            )
            for id_suffix, channel in _CHANNELS:
                _seed_capture_graph(connection, id_suffix, channel)
            # only the legit channel has a subscriber
            connection.execute(
                text(
                    "INSERT INTO user_channel "
                    "(user_id, channel_id, status, verify_attempt, added_at) "
                    "VALUES (:u, :c, 'verified', 0, now())"
                ),
                {"u": _USER_ID, "c": _LEGIT_CHANNEL},
            )

        # Upgrade through 0010 only: later migrations backfill from tables this
        # minimal fixture omits. 0010 is where the orphan-ordering bug lives.
        command.upgrade(cfg, "0010_user_owned_feed")  # was: PK abort on NULL user_id

        with engine.connect() as connection:
            surviving = {
                row[0]
                for row in connection.execute(
                    text("SELECT external_id FROM raw_message")
                )
            }
            events = connection.execute(
                text("SELECT count(*) FROM raw_signal_event")
            ).scalar_one()
            extracted = connection.execute(
                text("SELECT count(*) FROM extracted_signal")
            ).scalar_one()
        engine.dispose()

    assert surviving == {_LEGIT_CHANNEL}  # orphan raw_message purged
    assert events == 1  # orphan event + its derived children purged
    assert extracted == 1
