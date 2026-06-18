from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from verasig.storage.models import BacktestResultRow


def insert_result(
    session: Session,
    user_id: UUID,
    channel_id: int,
    score: int,
    win_rate: Decimal,
    pnl: Decimal,
    outcomes: list[dict],
    completed_at: datetime,
    result_id: UUID | None = None,
) -> BacktestResultRow:
    row = BacktestResultRow(
        id=result_id or uuid4(),
        user_id=user_id,
        external_id=channel_id,
        score=score,
        win_rate=win_rate,
        pnl=pnl,
        outcomes=outcomes,
        completed_at=completed_at,
    )
    session.add(row)
    session.flush()
    return row


def read_latest_results(
    session: Session, user_id: UUID
) -> dict[int, BacktestResultRow]:
    rows = session.scalars(
        select(BacktestResultRow)
        .where(BacktestResultRow.user_id == user_id)
        .order_by(BacktestResultRow.external_id, BacktestResultRow.completed_at.desc())
    ).all()
    latest: dict[int, BacktestResultRow] = {}
    for row in rows:
        latest.setdefault(row.external_id, row)
    return latest
