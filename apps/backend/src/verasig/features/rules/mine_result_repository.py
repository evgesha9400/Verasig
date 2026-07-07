"""Per-feed cache of the last template-mining result.

Stores the mine's ``{groups, messages}`` snapshot (camelCase wire shape) so
reopening a verified feed hydrates the Verify audit from it instead of re-running
the CPU-bound scan. One row per feed: a fresh mine upserts, deleting the feed
cascades it away."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.storage.models import MineResultRow


def read_mine_result(session: Session, user_id: UUID, external_id: int) -> dict | None:
    row = session.get(MineResultRow, (user_id, external_id))
    return dict(row.payload) if row else None


def upsert_mine_result(
    session: Session, user_id: UUID, external_id: int, payload: dict
) -> None:
    now = datetime.now(tz=UTC)
    statement = (
        pg_insert(MineResultRow.__table__)
        .values(
            user_id=user_id,
            external_id=external_id,
            payload=payload,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=["user_id", "external_id"],
            set_={"payload": payload, "updated_at": now},
        )
    )
    session.execute(statement)
    session.flush()
