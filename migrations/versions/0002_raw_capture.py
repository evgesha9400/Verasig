"""telegram_channel + raw_telegram_message tables (Slice 2).

Revision ID: 0002_raw_capture
Revises: 0001_baseline
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_raw_capture"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_channel",
        sa.Column("channel_id", sa.BigInteger(), primary_key=True),
        sa.Column("handle", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("is_private", sa.Boolean(), nullable=False),
        sa.Column("subscriber_count", sa.Integer(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_through_message_id", sa.BigInteger(), nullable=True),
    )
    op.create_table(
        "raw_telegram_message",
        sa.Column(
            "channel_id",
            sa.BigInteger(),
            sa.ForeignKey("telegram_channel.channel_id"),
            primary_key=True,
        ),
        sa.Column("message_id", sa.BigInteger(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("sender_id", sa.BigInteger(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reply_to_message_id", sa.BigInteger(), nullable=True),
        sa.Column("edit_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("has_media", sa.Boolean(), nullable=False),
        sa.Column("views", sa.Integer(), nullable=True),
        sa.Column("forwards", sa.Integer(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("raw_telegram_message")
    op.drop_table("telegram_channel")
