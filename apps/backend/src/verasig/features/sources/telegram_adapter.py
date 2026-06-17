"""Telegram adapter: connect / verify / status over the generic `source` row.

Replaces the old `user_telegram_link` CRUD. A user's Telegram connection lives in
one `source` (`name='Telegram'`); its secrets are folded into `config_encrypted`,
a JSON object whose `api_hash` / `session_string` are AES-GCM envelopes sealed with
the per-user AAD below — preserved verbatim from the pre-source schema so migrated
envelopes still decrypt. This module owns that codec; `source_repository` treats
`config_encrypted` as opaque.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from verasig.domain.source import TELEGRAM, Source
from verasig.domain.telegram_ports import TelegramAuth
from verasig.features.sources import source_repository
from verasig.foundation.security.secrets import SecretCipher
from verasig.storage.models import SourceRow


class TelegramLinkMissingError(Exception):
    """Raised when verification needs a pending Telegram source."""


def _aad(user_id: UUID) -> str:
    return f"{user_id}:telegram_link"


def mask_phone(phone: str) -> str:
    return f"{phone[:3]} •••• {phone[-4:]}"


def _config(
    api_id: int,
    api_hash_encrypted: str,
    phone: str,
    session_string_encrypted: str | None,
    phone_code_hash: str | None,
) -> dict:
    return {
        "api_id": api_id,
        "api_hash_encrypted": api_hash_encrypted,
        "phone": phone,
        "session_string_encrypted": session_string_encrypted,
        "phone_code_hash": phone_code_hash,
    }


async def connect(
    session: Session,
    user_id: UUID,
    api_id: int,
    api_hash: str,
    phone: str,
    auth: TelegramAuth,
    cipher: SecretCipher,
) -> SourceRow:
    pending = await auth.send_code(api_id, api_hash, phone)
    config = _config(
        api_id,
        cipher.encrypt(api_hash, _aad(user_id)),
        phone,
        cipher.encrypt(pending.session_string, _aad(user_id)),
        pending.phone_code_hash,
    )
    return source_repository.create_source(
        session, user_id, TELEGRAM, "pending", config, datetime.now(tz=UTC)
    )


async def verify(
    session: Session,
    user_id: UUID,
    code: str,
    auth: TelegramAuth,
    cipher: SecretCipher,
    password: str | None = None,
) -> SourceRow:
    source = source_repository.read_source(session, user_id, TELEGRAM)
    if source is None:
        raise TelegramLinkMissingError()
    config = source.config_encrypted
    if (
        config.get("session_string_encrypted") is None
        or config.get("phone_code_hash") is None
    ):
        raise TelegramLinkMissingError()
    api_hash = cipher.decrypt(config["api_hash_encrypted"], _aad(user_id))
    session_string = cipher.decrypt(config["session_string_encrypted"], _aad(user_id))
    final_session = await auth.sign_in(
        session_string,
        config["api_id"],
        api_hash,
        config["phone"],
        code,
        config["phone_code_hash"],
        password,
    )
    connected = _config(
        config["api_id"],
        config["api_hash_encrypted"],
        config["phone"],
        cipher.encrypt(final_session, _aad(user_id)),
        None,
    )
    return source_repository.create_source(
        session, user_id, TELEGRAM, "connected", connected, datetime.now(tz=UTC)
    )


def status(session: Session, user_id: UUID) -> dict:
    source = source_repository.read_source(session, user_id, TELEGRAM)
    if source is None:
        return {"connected": False, "phone": None}
    return {
        "connected": source.status == "connected",
        "phone": mask_phone(source.config_encrypted["phone"]),
    }


def read_connection(
    session: Session, user_id: UUID, cipher: SecretCipher
) -> Source | None:
    """The user's Telegram source with its connection secrets decrypted."""
    source = source_repository.read_source(session, user_id, TELEGRAM)
    if source is None:
        return None
    config = source.config_encrypted
    decrypted = {
        "api_id": config["api_id"],
        "api_hash": cipher.decrypt(config["api_hash_encrypted"], _aad(user_id)),
        "phone": config["phone"],
        "session_string": _decrypt_optional(
            cipher, config.get("session_string_encrypted"), user_id
        ),
        "phone_code_hash": config.get("phone_code_hash"),
    }
    return Source(name=source.name, status=source.status, config=decrypted)


def _decrypt_optional(
    cipher: SecretCipher, envelope: str | None, user_id: UUID
) -> str | None:
    return None if envelope is None else cipher.decrypt(envelope, _aad(user_id))
