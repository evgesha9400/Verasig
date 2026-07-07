from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from verasig.foundation.database.upsert import upsert_timestamped_row
from verasig.storage.models import ParserOverlayRow


def read_overlay(session: Session, user_id: UUID) -> dict:
    row = session.get(ParserOverlayRow, user_id)
    return dict(row.config) if row else {}


def upsert_overlay(session: Session, user_id: UUID, config: dict) -> None:
    upsert_timestamped_row(
        session,
        ParserOverlayRow.__table__,
        {"user_id": user_id},
        {"config": config},
        datetime.now(tz=UTC),
    )
