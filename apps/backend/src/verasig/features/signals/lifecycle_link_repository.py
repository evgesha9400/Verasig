from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.storage.models import LifecycleLinkRow


def insert_link(
    session: Session,
    user_id: UUID,
    channel_id: int,
    message_id: int,
    root_signal_id: UUID,
    created_at: datetime,
    link_id: UUID | None = None,
) -> LifecycleLinkRow:
    statement = pg_insert(LifecycleLinkRow).values(
        id=link_id or uuid4(),
        user_id=user_id,
        channel_id=channel_id,
        message_id=message_id,
        root_signal_id=root_signal_id,
        created_at=created_at,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[
            LifecycleLinkRow.user_id,
            LifecycleLinkRow.channel_id,
            LifecycleLinkRow.message_id,
        ],
        set_={
            "root_signal_id": statement.excluded.root_signal_id,
            "created_at": statement.excluded.created_at,
        },
    )
    session.execute(statement)
    session.flush()
    return session.scalars(
        select(LifecycleLinkRow).where(
            LifecycleLinkRow.user_id == user_id,
            LifecycleLinkRow.channel_id == channel_id,
            LifecycleLinkRow.message_id == message_id,
        )
    ).one()


def read_links(
    session: Session, user_id: UUID, channel_id: int
) -> list[LifecycleLinkRow]:
    return list(
        session.scalars(
            select(LifecycleLinkRow).where(
                LifecycleLinkRow.user_id == user_id,
                LifecycleLinkRow.channel_id == channel_id,
            )
        )
    )
