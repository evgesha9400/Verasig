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
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_phone: str | None = None
    session_path: str = "/session/telegram.session"
    backfill_batch_size: int = 200
    distiller_command: str = "claude"  # LLM CLI for rule distillation (go-ahead-gated)
    extractor_fallback_enabled: bool = True  # LLM fallback on deterministic miss
    extractor_command: str = "claude"  # LLM CLI for fallback extraction (gated)

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
