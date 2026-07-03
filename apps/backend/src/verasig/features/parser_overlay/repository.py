from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.storage.models import ParserOverlayRow


def read_overlay(session: Session, user_id: UUID) -> dict:
    row = session.get(ParserOverlayRow, user_id)
    return dict(row.config) if row else {}


def upsert_overlay(session: Session, user_id: UUID, config: dict) -> None:
    now = datetime.now(tz=UTC)
    statement = (
        pg_insert(ParserOverlayRow.__table__)
        .values(user_id=user_id, config=config, created_at=now, updated_at=now)
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_={"config": config, "updated_at": now},
        )
    )
    session.execute(statement)
    session.flush()
