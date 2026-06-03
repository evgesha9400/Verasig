from verasig.config import Settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("VERASIG_DATABASE_URL", "postgresql://u:p@db:5432/verasig")
    s = Settings()
    assert s.database_url.endswith("/verasig")
