"""Per-account parser overlay (custom aliases, direction tokens, reject phrases,
template thresholds) merged into the deterministic Template-Mining parser.

Revision ID: 0012_parser_overlay
Revises: 0011_generic_source
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0012_parser_overlay"
down_revision = "0011_generic_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parser_overlay",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("config", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", name="parser_overlay_pkey"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name="fk_parser_overlay_user",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("parser_overlay")
