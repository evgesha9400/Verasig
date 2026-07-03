"""Per-feed history depth: how far back a fresh capture reaches (ADR 0014).

A `feed` remembers the chosen capture depth (6 months / 1 year / all). It lives
in its own column, not `metadata`, because a backfill start overwrites the whole
`metadata` JSONB. Existing feeds default to one year.

Revision ID: 0013_feed_history_depth
Revises: 0012_parser_overlay
"""

import sqlalchemy as sa
from alembic import op

revision = "0013_feed_history_depth"
down_revision = "0012_parser_overlay"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "feed",
        sa.Column("history_depth", sa.String(), nullable=False, server_default="1y"),
    )
    op.create_check_constraint(
        "ck_feed_history_depth", "feed", "history_depth IN ('6m', '1y', 'all')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_feed_history_depth", "feed", type_="check")
    op.drop_column("feed", "history_depth")
