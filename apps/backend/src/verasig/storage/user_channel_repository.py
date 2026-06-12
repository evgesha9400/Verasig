from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.storage.models import (
    BacktestResultRow,
    ChatRiskConfigRow,
    ExtractedSignalRow,
    FilterDriftWarningRow,
    FilterRuleRow,
    GoldenLabelRow,
    LifecycleLinkRow,
    ParserDriftWarningRow,
    ParserRuleRow,
    RawSignalEventRow,
    UnrecognizedSignalRow,
    UserChannelRow,
)


def subscribe(
    session: Session, user_id: UUID, channel_id: int, added_at: datetime
) -> UserChannelRow:
    statement = pg_insert(UserChannelRow).values(
        user_id=user_id,
        channel_id=channel_id,
        status="new",
        verify_attempt=1,
        added_at=added_at,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[UserChannelRow.user_id, UserChannelRow.channel_id],
        set_={"status": statement.excluded.status},
    )
    session.execute(statement)
    session.flush()
    return read_subscription(session, user_id, channel_id)


def unsubscribe(session: Session, user_id: UUID, channel_id: int) -> None:
    event_ids = select(RawSignalEventRow.id).where(
        RawSignalEventRow.channel_id == channel_id
    )
    for row_type in (
        GoldenLabelRow,
        FilterRuleRow,
        ParserRuleRow,
        FilterDriftWarningRow,
        ParserDriftWarningRow,
        ExtractedSignalRow,
        UnrecognizedSignalRow,
        ChatRiskConfigRow,
        BacktestResultRow,
        LifecycleLinkRow,
    ):
        statement = delete(row_type).where(row_type.user_id == user_id)
        if hasattr(row_type, "channel_id"):
            statement = statement.where(row_type.channel_id == channel_id)
        if row_type is UnrecognizedSignalRow:
            statement = statement.where(row_type.event_id.in_(event_ids))
        session.execute(statement)
    session.execute(
        delete(UserChannelRow).where(
            UserChannelRow.user_id == user_id,
            UserChannelRow.channel_id == channel_id,
        )
    )


def read_subscriptions(session: Session, user_id: UUID) -> list[UserChannelRow]:
    return list(
        session.scalars(
            select(UserChannelRow)
            .where(UserChannelRow.user_id == user_id)
            .order_by(UserChannelRow.added_at)
        )
    )


def read_subscription(
    session: Session, user_id: UUID, channel_id: int
) -> UserChannelRow | None:
    return session.get(UserChannelRow, (user_id, channel_id))


def set_status(
    session: Session, user_id: UUID, channel_id: int, status: str
) -> UserChannelRow | None:
    row = read_subscription(session, user_id, channel_id)
    if row is None:
        return None
    row.status = status
    session.flush()
    return row


def bump_verify_attempt(session: Session, user_id: UUID, channel_id: int) -> int | None:
    row = read_subscription(session, user_id, channel_id)
    if row is None:
        return None
    row.verify_attempt += 1
    session.flush()
    return row.verify_attempt


def count_subscriptions(session: Session, user_id: UUID) -> int:
    return session.scalar(
        select(func.count())
        .select_from(UserChannelRow)
        .where(UserChannelRow.user_id == user_id)
    )
