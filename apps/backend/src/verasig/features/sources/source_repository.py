"""Source repository: a user's generic, provider-agnostic connection row.

Stores `config_encrypted` as an opaque JSON document (the Telegram adapter owns
its shape + the envelope codec); this layer only persists, reads, restatuses, and
deletes the row. Keyed for lookup by `(user_id, name)` (UNIQUE), so a user holds
at most one connection per provider. Deleting a source cascades its feeds + all
captured history via `feed.source_id`.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.storage.models import SourceRow


def create_source(
    session: Session,
    user_id: UUID,
    name: str,
    status: str,
    config_encrypted: dict,
    updated_at: datetime,
) -> SourceRow:
    """Insert the user's source for a provider, or refresh its status + config.

    Upserts on the `(user_id, name)` unique key so re-connecting overwrites the
    pending row; `created_at` is preserved on conflict.
    """
    statement = pg_insert(SourceRow).values(
        id=uuid4(),
        user_id=user_id,
        name=name,
        status=status,
        config_encrypted=config_encrypted,
        created_at=updated_at,
        updated_at=updated_at,
    )
    statement = statement.on_conflict_do_update(
        index_elements=["user_id", "name"],
        set_={
            "status": statement.excluded.status,
            "config_encrypted": statement.excluded.config_encrypted,
            "updated_at": statement.excluded.updated_at,
        },
    )
    session.execute(statement)
    session.flush()
    return read_source(session, user_id, name)


def read_source(session: Session, user_id: UUID, name: str) -> SourceRow | None:
    return session.scalar(
        select(SourceRow).where(SourceRow.user_id == user_id, SourceRow.name == name)
    )


def set_status(
    session: Session, user_id: UUID, name: str, status: str
) -> SourceRow | None:
    source = read_source(session, user_id, name)
    if source is None:
        return None
    source.status = status
    session.flush()
    return source


def delete_source(session: Session, user_id: UUID, name: str) -> None:
    session.execute(
        delete(SourceRow).where(SourceRow.user_id == user_id, SourceRow.name == name)
    )
