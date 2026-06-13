from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.storage.models import UserExchangeConnectionRow


def upsert_connection(
    session: Session,
    user_id: UUID,
    exchange_id: str,
    api_key_masked: str,
    api_key_encrypted: str,
    api_secret_encrypted: str,
    connected: bool,
    connected_at: datetime,
) -> UserExchangeConnectionRow:
    statement = pg_insert(UserExchangeConnectionRow).values(
        user_id=user_id,
        exchange_id=exchange_id,
        api_key_masked=api_key_masked,
        api_key_encrypted=api_key_encrypted,
        api_secret_encrypted=api_secret_encrypted,
        connected=connected,
        connected_at=connected_at,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[
            UserExchangeConnectionRow.user_id,
            UserExchangeConnectionRow.exchange_id,
        ],
        set_={
            "api_key_masked": statement.excluded.api_key_masked,
            "api_key_encrypted": statement.excluded.api_key_encrypted,
            "api_secret_encrypted": statement.excluded.api_secret_encrypted,
            "connected": statement.excluded.connected,
            "connected_at": statement.excluded.connected_at,
        },
    )
    session.execute(statement)
    session.flush()
    return session.get(UserExchangeConnectionRow, (user_id, exchange_id))


def set_connected(
    session: Session, user_id: UUID, exchange_id: str, connected: bool
) -> UserExchangeConnectionRow | None:
    row = session.get(UserExchangeConnectionRow, (user_id, exchange_id))
    if row is None:
        return None
    row.connected = connected
    session.flush()
    return row


def read_connections(
    session: Session, user_id: UUID
) -> list[UserExchangeConnectionRow]:
    return list(
        session.scalars(
            select(UserExchangeConnectionRow).where(
                UserExchangeConnectionRow.user_id == user_id
            )
        )
    )
