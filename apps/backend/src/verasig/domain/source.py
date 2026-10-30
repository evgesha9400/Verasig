from dataclasses import dataclass

# the only provider `source.name` allows today (mirrors the ck_source_name check)
TELEGRAM = "Telegram"


@dataclass(frozen=True)
class Source:
    """A user's connection to a provider, with its config already decrypted.

    `config` is the provider-specific connection secrets in plaintext; the
    Telegram adapter owns its shape and the encrypt/decrypt round-trip.
    """

    name: str
    status: str
    config: dict
