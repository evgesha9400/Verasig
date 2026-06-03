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


@pytest.fixture
def session_factory(migrated_engine):
    # clean slate per test (raw + channel tables); FK cascade clears children
    with migrated_engine.begin() as connection:
        connection.execute(
            text("TRUNCATE raw_telegram_message, telegram_channel CASCADE")
        )
    return sessionmaker(bind=migrated_engine, future=True)


@pytest.fixture
def db_session(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
