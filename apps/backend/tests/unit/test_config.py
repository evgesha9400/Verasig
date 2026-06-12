from verasig.config import Settings


def test_database_url_defaults_to_localhost_parts():
    assert (
        Settings(_env_file=None).database_url
        == "postgresql+psycopg://verasig:verasig@localhost:5432/verasig"
    )


def test_database_url_assembles_from_db_env(monkeypatch):
    monkeypatch.setenv("VERASIG_DB_HOST", "db")
    monkeypatch.setenv("VERASIG_DB_PORT", "6543")
    monkeypatch.setenv("VERASIG_DB_NAME", "signals")
    monkeypatch.setenv("VERASIG_DB_USER", "observer")
    monkeypatch.setenv("VERASIG_DB_PASSWORD", "secret")

    assert (
        Settings().database_url
        == "postgresql+psycopg://observer:secret@db:6543/signals"
    )


def test_database_url_override_takes_precedence(monkeypatch):
    override = "postgresql+psycopg://u:p@override:5432/verasig"
    monkeypatch.setenv("VERASIG_DATABASE_URL_OVERRIDE", override)
    monkeypatch.setenv("VERASIG_DB_HOST", "db")

    assert Settings().database_url == override


def test_database_url_escapes_user_password_and_database_name(monkeypatch):
    monkeypatch.setenv("VERASIG_DB_USER", "u@name")
    monkeypatch.setenv("VERASIG_DB_PASSWORD", "p@ss/word")
    monkeypatch.setenv("VERASIG_DB_NAME", "vera sig")

    assert (
        Settings().database_url
        == "postgresql+psycopg://u%40name:p%40ss%2Fword@localhost:5432/vera%20sig"
    )


def test_telegram_phone_loads_from_env(monkeypatch):
    monkeypatch.setenv("VERASIG_TELEGRAM_PHONE", "+15551234567")
    assert Settings().telegram_phone == "+15551234567"


def test_telegram_phone_defaults_to_none():
    assert Settings(_env_file=None).telegram_phone is None


def test_backfill_batch_size_defaults_to_200():
    assert Settings(_env_file=None).backfill_batch_size == 200


def test_backfill_batch_size_loads_from_env(monkeypatch):
    monkeypatch.setenv("VERASIG_BACKFILL_BATCH_SIZE", "50")
    assert Settings().backfill_batch_size == 50


def test_distiller_command_defaults_to_claude():
    assert Settings(_env_file=None).distiller_command == "claude"


def test_distiller_command_loads_from_env(monkeypatch):
    monkeypatch.setenv("VERASIG_DISTILLER_COMMAND", "codex")
    assert Settings().distiller_command == "codex"


def test_extractor_fallback_enabled_defaults_to_true():
    assert Settings(_env_file=None).extractor_fallback_enabled is True


def test_extractor_fallback_enabled_loads_from_env(monkeypatch):
    monkeypatch.setenv("VERASIG_EXTRACTOR_FALLBACK_ENABLED", "false")
    assert Settings().extractor_fallback_enabled is False


def test_extractor_command_defaults_to_claude():
    assert Settings(_env_file=None).extractor_command == "claude"


def test_extractor_command_loads_from_env(monkeypatch):
    monkeypatch.setenv("VERASIG_EXTRACTOR_COMMAND", "codex")
    assert Settings().extractor_command == "codex"


def test_settings_carry_api_secrets(monkeypatch):
    monkeypatch.setenv("VERASIG_JWT_SECRET", "jwt-secret")
    monkeypatch.setenv("VERASIG_SECRET_KEYS", "2026-06:newb64key,2026-01:oldb64key")

    settings = Settings(_env_file=None)

    assert settings.jwt_secret == "jwt-secret"
    assert settings.secret_keys == "2026-06:newb64key,2026-01:oldb64key"
    assert settings.anthropic_model == "claude-sonnet-4-6"
    assert settings.cors_origins == ["http://localhost:5173"]
