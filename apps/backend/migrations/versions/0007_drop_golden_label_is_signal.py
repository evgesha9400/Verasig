"""drop duplicate golden label signal column.

Revision ID: 0007_drop_golden_label_is_signal
Revises: 0006_multi_tenant_api
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_drop_golden_label_is_signal"
down_revision = "0006_multi_tenant_api"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("golden_label", "is_signal")


def downgrade() -> None:
    op.add_column("golden_label", sa.Column("is_signal", sa.Boolean(), nullable=True))
    op.execute("UPDATE golden_label SET is_signal = (label = 'signal')")
    op.alter_column("golden_label", "is_signal", nullable=False)
