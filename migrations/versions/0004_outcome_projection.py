"""recomputable per-event outcome projection (ADR 0006).

Adds parser_drift_warning (deterministic miss + fallback success) and
UNIQUE(event_id) on extracted_signal + unrecognized_signal, so record_outcome can
upsert the winning outcome and delete the losing sibling per event. Raw tables
stay append-only; only this projection is recomputed.

Revision ID: 0004_outcome_projection
Revises: 0003_distillation
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_outcome_projection"
down_revision = "0003_distillation"
branch_labels = None
depends_on = None

_EVENT_FK = "raw_signal_event.id"


def upgrade() -> None:
    op.create_table(
        "parser_drift_warning",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey(_EVENT_FK), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("deterministic_result", sa.String(), nullable=False),
        sa.Column("fallback_result", sa.String(), nullable=False),
        sa.Column("fallback_signal_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id", name="uq_parser_drift_event"),
    )
    op.create_unique_constraint(
        "uq_extracted_signal_event", "extracted_signal", ["event_id"]
    )
    op.create_unique_constraint(
        "uq_unrecognized_signal_event", "unrecognized_signal", ["event_id"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_unrecognized_signal_event", "unrecognized_signal", type_="unique"
    )
    op.drop_constraint("uq_extracted_signal_event", "extracted_signal", type_="unique")
    op.drop_table("parser_drift_warning")
