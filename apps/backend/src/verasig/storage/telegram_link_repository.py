from datetime import datetime
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.storage.models import UserTelegramLinkRow


def upsert_pending(
    session: Session,
    user_id: UUID,
    api_id: int,
    api_hash_encrypted: str,
    phone: str,
    phone_code_hash: str,
    updated_at: datetime,
    session_string_encrypted: str | None = None,
) -> UserTelegramLinkRow:
    statement = pg_insert(UserTelegramLinkRow).values(
        user_id=user_id,
        api_id=api_id,
        api_hash_encrypted=api_hash_encrypted,
        phone=phone,
        session_string_encrypted=session_string_encrypted,
        phone_code_hash=phone_code_hash,
        status="pending",
        updated_at=updated_at,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[UserTelegramLinkRow.user_id],
        set_={
            "api_id": statement.excluded.api_id,
            "api_hash_encrypted": statement.excluded.api_hash_encrypted,
            "phone": statement.excluded.phone,
            "session_string_encrypted": statement.excluded.session_string_encrypted,
            "phone_code_hash": statement.excluded.phone_code_hash,
            "status": statement.excluded.status,
            "updated_at": statement.excluded.updated_at,
        },
    )
    session.execute(statement)
    session.flush()
    return read_link(session, user_id)


def mark_connected(
    session: Session, user_id: UUID, session_string_encrypted: str, updated_at: datetime
) -> UserTelegramLinkRow | None:
    row = session.get(UserTelegramLinkRow, user_id)
    if row is None:
        return None
    row.session_string_encrypted = session_string_encrypted
    row.phone_code_hash = None
    row.status = "connected"
    row.updated_at = updated_at
    session.flush()
    return row


def read_link(session: Session, user_id: UUID) -> UserTelegramLinkRow | None:
    return session.get(UserTelegramLinkRow, user_id)
