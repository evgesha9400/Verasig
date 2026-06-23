from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsError(ValueError):
    """Raised when required runtime settings are missing or invalid."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VERASIG_",
        env_file=".env",
        extra="ignore",
    )

    database_url_override: str | None = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "verasig"
    db_user: str = "verasig"
    db_password: str = "verasig"
    env: str = "local"
    backfill_batch_size: int = 200
    jwt_secret: str = "dev-secret"
    jwt_ttl_days: int = 7
    secret_keys: str = ""
    claude_code_oauth_token: str = ""
    claude_code_model: str = "sonnet"
    claude_code_timeout_seconds: int = 600
    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        user = quote(self.db_user, safe="")
        password = quote(self.db_password, safe="")
        database = quote(self.db_name, safe="")
        return (
            f"postgresql+psycopg://{user}:{password}"
            f"@{self.db_host}:{self.db_port}/{database}"
        )

    def secret_key_spec(self) -> str:
        spec = self.secret_keys.strip()
        if not spec:
            raise SettingsError(
                "VERASIG_SECRET_KEYS must be set to a comma-separated "
                "key_id:base64key keyring"
            )
        return spec

    def jwt_secret_spec(self) -> str:
        secret = self.jwt_secret.strip()
        if not secret:
            raise SettingsError("VERASIG_JWT_SECRET must not be blank")
        env = self.env.strip().lower() or "local"
        if secret == "dev-secret" and env != "local":
            raise SettingsError(
                "VERASIG_JWT_SECRET=dev-secret is only allowed when VERASIG_ENV=local"
            )
        if env != "local" and len(secret) < 32:
            raise SettingsError(
                "VERASIG_JWT_SECRET must be at least 32 characters outside "
                "local environments"
            )
        return secret
