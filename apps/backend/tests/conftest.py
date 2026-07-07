import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def pg_url():
    with PostgresContainer("postgres:16") as pg:
        yield pg.get_connection_url().replace("psycopg2", "psycopg")


@pytest.fixture(scope="session")
def migrated_engine(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")
    engine = create_engine(pg_url, future=True)
    yield engine
    engine.dispose()


_ALL_TABLES = ", ".join(
    [
        "raw_message",
        "raw_signal_event",
        "extracted_signal",
        "unrecognized_signal",
        "deleted_signal_evidence",
        "user_account",
        "source",
        "feed",
        "backfill_job_run",
        "user_exchange_connection",
        "feed_risk_config",
        "backtest_result",
        "lifecycle_link",
        "mine_result",
    ]
)


@pytest.fixture
def session_factory(migrated_engine):
    # clean slate per test; CASCADE clears FK children, explicit list covers
    # the nullable-FK rule tables (global rules would otherwise survive)
    with migrated_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {_ALL_TABLES} CASCADE"))
    return sessionmaker(bind=migrated_engine, future=True)


@pytest.fixture
def db_session(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
