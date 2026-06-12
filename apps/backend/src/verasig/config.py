from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    backfill_batch_size: int = 200
    jwt_secret: str = "dev-secret"
    jwt_ttl_days: int = 7
    secret_keys: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
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
