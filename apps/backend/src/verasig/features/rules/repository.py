"""Rule repository functions.

Domain rules/labels speak `channel_id`/`message_id`; storage speaks
`external_id`/`external_message_id` and is user-owned, so reads/writes translate.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from verasig.domain.label import GoldenLabel
from verasig.storage.models import GoldenLabelRow


def upsert_labels(session: Session, labels: list[GoldenLabel]) -> None:
    for label in labels:
        statement = pg_insert(GoldenLabelRow).values(
            id=label.id,
            user_id=label.user_id,
            external_id=label.channel_id,
            external_message_id=label.message_id,
            label=label.label.value,
            expected=(
                label.expected.model_dump(mode="json") if label.expected else None
            ),
            labeled_at=label.labeled_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["user_id", "external_id", "external_message_id"],
            set_={
                "label": statement.excluded.label,
                "expected": statement.excluded.expected,
                "labeled_at": statement.excluded.labeled_at,
            },
        )
        session.execute(statement)


def _label_from_row(row: GoldenLabelRow) -> GoldenLabel:
    return GoldenLabel(
        id=row.id,
        user_id=row.user_id,
        channel_id=row.external_id,
        message_id=row.external_message_id,
        label=row.label,
        expected=row.expected,
        labeled_at=row.labeled_at,
    )


def read_labels(session: Session, channel_id: int, user_id: UUID) -> list[GoldenLabel]:
    rows = session.scalars(
        select(GoldenLabelRow)
        .where(
            GoldenLabelRow.external_id == channel_id,
            GoldenLabelRow.user_id == user_id,
        )
        .order_by(GoldenLabelRow.labeled_at, GoldenLabelRow.external_message_id)
    ).all()
    return [_label_from_row(row) for row in rows]
