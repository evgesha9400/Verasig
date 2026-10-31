import base64
import binascii
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_KEY = bytes(32)
_SMTP_TLS_MODES = ("none", "starttls", "ssl")


class SettingsError(ValueError):
    """Raised when required runtime settings are missing or invalid."""


@dataclass(frozen=True)
class MailConfig:
    host: str
    port: int
    user: str
    password: str
    tls: str
    sender: str


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
    cors_origins: list[str] = ["http://localhost:5173"]
    web_dist_dir: Path | None = None
    # Stripe billing. Blank values fail at request time (see the *_spec methods).
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_trader_monthly: str = ""
    stripe_price_trader_yearly: str = ""
    # Public origin of the web app: Checkout and the portal return here.
    site_url: str = "http://localhost:5173"
    # Outgoing mail over SMTP. A blank host logs mail instead, locally only.
    smtp_host: str = ""
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: str = "none"
    mail_from: str = "Verasig <no-reply@verasig.io>"

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        if self.db_password == "verasig" and not self._is_local():
            raise SettingsError(
                "VERASIG_DB_PASSWORD=verasig is only allowed when VERASIG_ENV=local"
            )
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
        if not self._is_local() and any(
            _is_dev_key(entry) for entry in spec.split(",")
        ):
            raise SettingsError(
                "VERASIG_SECRET_KEYS must not contain the development key "
                "outside local environments"
            )
        return spec

    def jwt_secret_spec(self) -> str:
        secret = self.jwt_secret.strip()
        if not secret:
            raise SettingsError("VERASIG_JWT_SECRET must not be blank")
        if secret == "dev-secret" and not self._is_local():
            raise SettingsError(
                "VERASIG_JWT_SECRET=dev-secret is only allowed when VERASIG_ENV=local"
            )
        if not self._is_local() and len(secret) < 32:
            raise SettingsError(
                "VERASIG_JWT_SECRET must be at least 32 characters outside "
                "local environments"
            )
        return secret

    def stripe_secret_key_spec(self) -> str:
        return _required("VERASIG_STRIPE_SECRET_KEY", self.stripe_secret_key)

    def stripe_webhook_secret_spec(self) -> str:
        return _required("VERASIG_STRIPE_WEBHOOK_SECRET", self.stripe_webhook_secret)

    def stripe_trader_price_spec(self, interval: str) -> str:
        if interval == "year":
            return _required(
                "VERASIG_STRIPE_PRICE_TRADER_YEARLY", self.stripe_price_trader_yearly
            )
        return _required(
            "VERASIG_STRIPE_PRICE_TRADER_MONTHLY", self.stripe_price_trader_monthly
        )

    def site_url_spec(self) -> str:
        return _required("VERASIG_SITE_URL", self.site_url).rstrip("/")

    def mail_spec(self) -> MailConfig | None:
        host = self.smtp_host.strip()
        if not host:
            if self._is_local():
                return None
            raise SettingsError(
                "VERASIG_SMTP_HOST must be set outside local environments"
            )
        tls = self.smtp_tls.strip().lower()
        if tls not in _SMTP_TLS_MODES:
            raise SettingsError(
                f"VERASIG_SMTP_TLS must be one of {', '.join(_SMTP_TLS_MODES)}"
            )
        return MailConfig(
            host=host,
            port=self.smtp_port,
            user=self.smtp_user.strip(),
            password=self.smtp_password.strip(),
            tls=tls,
            sender=self.mail_from.strip(),
        )

    def _is_local(self) -> bool:
        return (self.env.strip().lower() or "local") == "local"


def _is_dev_key(entry: str) -> bool:
    """A keyring entry whose key decodes to the all-zero development key.

    Entries that fail to decode are left for SecretCipher.from_spec to reject.
    """
    _, _, encoded = entry.strip().partition(":")
    try:
        return base64.b64decode(encoded, validate=True) == _DEV_KEY
    except binascii.Error:
        return False


def _required(name: str, value: str) -> str:
    if not value.strip():
        raise SettingsError(f"{name} must be set to use billing")
    return value.strip()
