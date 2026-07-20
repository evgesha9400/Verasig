"""Persist revisioned MiningReview snapshots.

Revision ID: 0002_revisioned_mining_review
Revises: 0001_init
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_revisioned_mining_review"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "feed",
        sa.Column(
            "capture_generation",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
    )
    # The singleton cache has no input identity and therefore cannot safely be
    # promoted into a review. Discard it rather than presenting legacy data as
    # current; a fresh mine creates the first revisioned review.
    op.drop_table("mine_result")
    op.create_table(
        "mining_review",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("input_revision", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("overlay", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "accepted_template_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "missed_message_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id", "external_id"],
            ["feed.user_id", "feed.external_id"],
            name="fk_mining_review_feed",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name="fk_mining_review_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mining_review_feed_created",
        "mining_review",
        ["user_id", "external_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_mining_review_feed_created", table_name="mining_review")
    op.drop_table("mining_review")
    op.create_table(
        "mine_result",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id", "external_id"],
            ["feed.user_id", "feed.external_id"],
            name="fk_mine_result_feed",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name="fk_mine_result_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "external_id"),
    )
    op.drop_column("feed", "capture_generation")
