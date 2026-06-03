from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VERASIG_", env_file=".env")

    database_url: str = "postgresql+psycopg://verasig:verasig@db:5432/verasig"
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_phone: str | None = None
    session_path: str = "/session/telegram.session"
    backfill_batch_size: int = 200
