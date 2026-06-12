from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from verasig.domain.protocols import CodeInvalidError, TelegramAuth
from verasig.foundation.security import SecretCipher
from verasig.storage import telegram_link_repository
from verasig.storage.models import UserTelegramLinkRow


class TelegramLinkMissingError(Exception):
    """Raised when verification needs a pending Telegram link."""


def _aad(user_id: UUID) -> str:
    return f"{user_id}:telegram_link"


def mask_phone(phone: str) -> str:
    return f"{phone[:3]} •••• {phone[-4:]}"


async def connect(
    session: Session,
    user_id: UUID,
    api_id: int,
    api_hash: str,
    phone: str,
    auth: TelegramAuth,
    cipher: SecretCipher,
) -> UserTelegramLinkRow:
    pending = await auth.send_code(api_id, api_hash, phone)
    return telegram_link_repository.upsert_pending(
        session,
        user_id,
        api_id,
        cipher.encrypt(api_hash, _aad(user_id)),
        phone,
        pending.phone_code_hash,
        datetime.now(tz=UTC),
        session_string_encrypted=cipher.encrypt(pending.session_string, _aad(user_id)),
    )


async def verify(
    session: Session,
    user_id: UUID,
    code: str,
    auth: TelegramAuth,
    cipher: SecretCipher,
) -> UserTelegramLinkRow:
    link = telegram_link_repository.read_link(session, user_id)
    if (
        link is None
        or link.session_string_encrypted is None
        or link.phone_code_hash is None
    ):
        raise TelegramLinkMissingError()
    api_hash = cipher.decrypt(link.api_hash_encrypted, _aad(user_id))
    session_string = cipher.decrypt(link.session_string_encrypted, _aad(user_id))
    try:
        final_session = await auth.sign_in(
            session_string,
            link.api_id,
            api_hash,
            link.phone,
            code,
            link.phone_code_hash,
        )
    except CodeInvalidError:
        raise
    return telegram_link_repository.mark_connected(
        session,
        user_id,
        cipher.encrypt(final_session, _aad(user_id)),
        datetime.now(tz=UTC),
    )


def status(session: Session, user_id: UUID) -> dict:
    link = telegram_link_repository.read_link(session, user_id)
    if link is None:
        return {"connected": False, "phone": None}
    return {
        "connected": link.status == "connected",
        "phone": mask_phone(link.phone),
    }
