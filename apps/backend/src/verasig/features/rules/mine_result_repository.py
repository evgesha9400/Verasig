"""Per-feed cache of the last template-mining result.

Stores the mine's ``{groups, messages}`` snapshot (camelCase wire shape) so
reopening a verified feed hydrates the Verify audit from it instead of re-running
the CPU-bound scan. One row per feed: a fresh mine upserts, deleting the feed
cascades it away."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from verasig.foundation.database.upsert import upsert_timestamped_row
from verasig.storage.models import MineResultRow


def read_mine_result(session: Session, user_id: UUID, external_id: int) -> dict | None:
    row = session.get(MineResultRow, (user_id, external_id))
    return dict(row.payload) if row else None


def upsert_mine_result(
    session: Session, user_id: UUID, external_id: int, payload: dict
) -> None:
    upsert_timestamped_row(
        session,
        MineResultRow.__table__,
        {"user_id": user_id, "external_id": external_id},
        {"payload": payload},
        datetime.now(tz=UTC),
    )
