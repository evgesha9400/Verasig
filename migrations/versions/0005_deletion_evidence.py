"""durable, non-recomputable deletion evidence (ADR 0008).

Adds deleted_signal_evidence — the third storage class. One row per
(channel_id, message_id) (UNIQUE) so rescans are idempotent; the repo upsert
upgrades SUSPECTED->CONFIRMED only and preserves the first-noticed detected_at.
Unlike the recomputable projection, this evidence is persisted because the live
snapshot it is diffed against is ephemeral and retained nowhere.

Revision ID: 0005_deletion_evidence
Revises: 0004_outcome_projection
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_deletion_evidence"
down_revision = "0004_outcome_projection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deleted_signal_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "channel_id",
            sa.BigInteger(),
            sa.ForeignKey("telegram_channel.channel_id"),
            nullable=False,
        ),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("confidence", sa.String(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("was_signal_candidate", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("channel_id", "message_id", name="uq_deleted_evidence_msg"),
    )


def downgrade() -> None:
    op.drop_table("deleted_signal_evidence")
