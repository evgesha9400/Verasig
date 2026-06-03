"""Empty baseline: establishes the Alembic revision chain.

Real tables arrive in Slice 2 (TelegramChannel, RawTelegramMessage).

Revision ID: 0001_baseline
Revises:
"""

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
