from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from verasig.domain.label import GoldenLabel, LabelKind
from verasig.services.projection.messages import (
    project_message,
    read_replies_by_message_id,
)
from verasig.storage.models import (
    ChannelRow,
    GoldenLabelRow,
    RawMessageRow,
    RawSignalEventRow,
)
from verasig.storage.rule_repository import upsert_labels


def labeling_sample(
    session: Session, user_id: UUID, channel_id: int, limit: int
) -> list[dict]:
    channel = session.get(ChannelRow, channel_id)
    labeled = (
        select(GoldenLabelRow.message_id)
        .where(
            GoldenLabelRow.user_id == user_id,
            GoldenLabelRow.channel_id == channel_id,
        )
        .subquery()
    )
    rows = session.scalars(
        select(RawMessageRow)
        .join(
            RawSignalEventRow,
            (RawSignalEventRow.channel_id == RawMessageRow.channel_id)
            & (RawSignalEventRow.message_id == RawMessageRow.message_id),
        )
        .where(
            RawMessageRow.channel_id == channel_id,
            RawMessageRow.message_id.not_in(select(labeled.c.message_id)),
        )
        .order_by(RawMessageRow.posted_at, RawMessageRow.message_id)
        .limit(limit)
    ).all()
    replies = read_replies_by_message_id(session, channel_id, rows)
    return [
        project_message(row, channel, replies.get(row.reply_to_message_id))
        for row in rows
    ]


def record_label(
    session: Session, user_id: UUID, channel_id: int, message_id: int, label: LabelKind
) -> None:
    upsert_labels(
        session,
        [
            GoldenLabel(
                user_id=user_id,
                channel_id=channel_id,
                message_id=message_id,
                label=label,
                labeled_at=datetime.now(tz=UTC),
            )
        ],
    )


def label_counts(session: Session, user_id: UUID, channel_id: int) -> dict:
    rows = session.execute(
        select(GoldenLabelRow.label, func.count())
        .where(
            GoldenLabelRow.user_id == user_id, GoldenLabelRow.channel_id == channel_id
        )
        .group_by(GoldenLabelRow.label)
    ).all()
    counts = {label: count for label, count in rows}
    signal = counts.get(LabelKind.SIGNAL.value, 0)
    noise = counts.get(LabelKind.NOISE.value, 0)
    modifier = counts.get(LabelKind.MODIFIER.value, 0)
    return {
        "signalCount": signal,
        "noiseCount": noise,
        "modifierCount": modifier,
        "total": signal + noise + modifier,
    }
