from alembic import command
from alembic.config import Config


def test_migrations_apply(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", pg_url)
    command.upgrade(cfg, "head")  # no error == migrations apply
