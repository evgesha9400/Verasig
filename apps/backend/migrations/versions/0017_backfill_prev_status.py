"""Persist the feed status a backfill run started from.

A run interrupted by a service restart must restore the reviewed feed status
(verified/analyzed) rather than fall to "failed". The coordinator used to keep
this in an in-memory map that does not survive a restart, so recovery on boot
always lost it. Persisting it on the run row makes recovery durable.

Revision ID: 0017_backfill_prev_status
Revises: 0016_drop_legacy_rule_schema
"""

import sqlalchemy as sa
from alembic import op

revision = "0017_backfill_prev_status"
down_revision = "0016_drop_legacy_rule_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "backfill_job_run",
        sa.Column("previous_feed_status", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("backfill_job_run", "previous_feed_status")
