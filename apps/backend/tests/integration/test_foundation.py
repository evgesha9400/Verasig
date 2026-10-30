from sqlalchemy import text

from verasig.config import Settings
from verasig.foundation.database.session import make_engine


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv(
        "VERASIG_DATABASE_URL_OVERRIDE", "postgresql://u:p@db:5432/verasig"
    )
    s = Settings(_env_file=None)
    assert s.database_url.endswith("/verasig")


def test_health_connects(pg_url):
    engine = make_engine(pg_url)
    with engine.connect() as conn:
        assert conn.execute(text("select 1")).scalar() == 1
