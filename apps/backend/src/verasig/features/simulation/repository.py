from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import delete, select
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


def delete_results_for_channel(
    session: Session, user_id: UUID, channel_id: int
) -> None:
    """Drop a feed's backtests once its signals or risk model change, so no
    result outlives the inputs it was computed from."""
    session.execute(
        delete(BacktestResultRow).where(
            BacktestResultRow.user_id == user_id,
            BacktestResultRow.external_id == channel_id,
        )
    )


def read_latest_results(
    session: Session, user_id: UUID
) -> dict[int, BacktestResultRow]:
    # DISTINCT ON keeps only each feed's newest result in Postgres.
    rows = session.scalars(
        select(BacktestResultRow)
        .where(BacktestResultRow.user_id == user_id)
        .distinct(BacktestResultRow.external_id)
        .order_by(BacktestResultRow.external_id, BacktestResultRow.completed_at.desc())
    ).all()
    return {row.external_id: row for row in rows}
