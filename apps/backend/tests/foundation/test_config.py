import pytest

from verasig.config import Settings, SettingsError

CONFIG_ENV_KEYS = (
    "VERASIG_DATABASE_URL_OVERRIDE",
    "VERASIG_DB_HOST",
    "VERASIG_DB_PORT",
    "VERASIG_DB_NAME",
    "VERASIG_DB_USER",
    "VERASIG_DB_PASSWORD",
    "VERASIG_BACKFILL_BATCH_SIZE",
    "VERASIG_ENV",
    "VERASIG_JWT_SECRET",
    "VERASIG_JWT_TTL_DAYS",
    "VERASIG_CORS_ORIGINS",
    "VERASIG_SECRET_KEYS",
    "VERASIG_CLAUDE_CODE_OAUTH_TOKEN",
    "VERASIG_CLAUDE_CODE_MODEL",
    "VERASIG_CLAUDE_CODE_TIMEOUT_SECONDS",
)


@pytest.fixture(autouse=True)
def isolate_settings_environment(monkeypatch):
    for key in CONFIG_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


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
        Settings(_env_file=None).database_url
        == "postgresql+psycopg://observer:secret@db:6543/signals"
    )


def test_database_url_loads_from_explicit_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "VERASIG_DB_HOST=file-db",
                "VERASIG_DB_PORT=6543",
                "VERASIG_DB_NAME=signals",
                "VERASIG_DB_USER=observer",
                "VERASIG_DB_PASSWORD=secret",
            ]
        )
    )

    assert (
        Settings(_env_file=env_file).database_url
        == "postgresql+psycopg://observer:secret@file-db:6543/signals"
    )


def test_database_url_override_takes_precedence(monkeypatch):
    override = "postgresql+psycopg://u:p@override:5432/verasig"
    monkeypatch.setenv("VERASIG_DATABASE_URL_OVERRIDE", override)
    monkeypatch.setenv("VERASIG_DB_HOST", "db")

    assert Settings(_env_file=None).database_url == override


def test_database_url_escapes_user_password_and_database_name(monkeypatch):
    monkeypatch.setenv("VERASIG_DB_USER", "u@name")
    monkeypatch.setenv("VERASIG_DB_PASSWORD", "p@ss/word")
    monkeypatch.setenv("VERASIG_DB_NAME", "vera sig")

    assert (
        Settings(_env_file=None).database_url
        == "postgresql+psycopg://u%40name:p%40ss%2Fword@localhost:5432/vera%20sig"
    )


def test_backfill_batch_size_defaults_to_200():
    assert Settings(_env_file=None).backfill_batch_size == 200


def test_backfill_batch_size_loads_from_env(monkeypatch):
    monkeypatch.setenv("VERASIG_BACKFILL_BATCH_SIZE", "50")
    assert Settings(_env_file=None).backfill_batch_size == 50


def test_settings_carry_api_secrets(monkeypatch):
    monkeypatch.setenv("VERASIG_ENV", "local")
    monkeypatch.setenv("VERASIG_JWT_SECRET", "jwt-secret")
    monkeypatch.setenv("VERASIG_SECRET_KEYS", "2026-06:newb64key,2026-01:oldb64key")

    settings = Settings(_env_file=None)

    assert settings.jwt_secret == "jwt-secret"
    assert settings.secret_keys == "2026-06:newb64key,2026-01:oldb64key"
    assert settings.cors_origins == ["http://localhost:5173"]


def test_secret_key_spec_returns_configured_keyring(monkeypatch):
    keyring = "2026-06:newb64key,2026-01:oldb64key"
    monkeypatch.setenv("VERASIG_SECRET_KEYS", keyring)

    assert Settings(_env_file=None).secret_key_spec() == keyring


def test_secret_key_spec_rejects_blank_keyring():
    settings = Settings(_env_file=None, secret_keys="   ")

    with pytest.raises(
        SettingsError,
        match="VERASIG_SECRET_KEYS must be set to a comma-separated "
        "key_id:base64key keyring",
    ):
        settings.secret_key_spec()


def test_jwt_secret_spec_accepts_local_dev_secret(monkeypatch):
    monkeypatch.setenv("VERASIG_ENV", "local")
    settings = Settings(_env_file=None, jwt_secret="dev-secret")

    assert settings.jwt_secret_spec() == "dev-secret"


def test_jwt_secret_spec_rejects_dev_secret_outside_local(monkeypatch):
    monkeypatch.setenv("VERASIG_ENV", "production")

    with pytest.raises(
        SettingsError,
        match="VERASIG_JWT_SECRET=dev-secret is only allowed when VERASIG_ENV=local",
    ):
        Settings(_env_file=None, jwt_secret="dev-secret").jwt_secret_spec()


def test_jwt_secret_spec_rejects_blank_secret():
    settings = Settings(_env_file=None, jwt_secret="   ")

    with pytest.raises(SettingsError, match="VERASIG_JWT_SECRET must not be blank"):
        settings.jwt_secret_spec()


def test_jwt_secret_spec_rejects_short_secret_when_not_local(monkeypatch):
    monkeypatch.setenv("VERASIG_ENV", "staging")

    with pytest.raises(
        SettingsError,
        match="VERASIG_JWT_SECRET must be at least 32 characters outside "
        "local environments",
    ):
        Settings(_env_file=None, jwt_secret="s" * 16).jwt_secret_spec()


def test_jwt_secret_spec_accepts_strong_secret_when_not_local(monkeypatch):
    monkeypatch.setenv("VERASIG_ENV", "staging")

    assert Settings(_env_file=None, jwt_secret="s" * 32).jwt_secret_spec() == "s" * 32
