"""Per-feed template-mining result cache.

Stores the last mine's ``{groups, messages}`` snapshot (camelCase wire shape) so
reopening a verified feed hydrates the Verify audit from it instead of re-running
the CPU-bound scan over the whole message history. One row per feed; a fresh mine
upserts it, deleting the feed cascades it away.

Revision ID: 0019_mine_result
Revises: 0018_exchange_user_cascade
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0019_mine_result"
down_revision = "0018_exchange_user_cascade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mine_result",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.BigInteger(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "external_id", name="mine_result_pkey"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name="fk_mine_result_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "external_id"],
            ["feed.user_id", "feed.external_id"],
            name="fk_mine_result_feed",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("mine_result")
