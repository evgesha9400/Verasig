"""Drop unrecognized_signal; drop the constant extracted_signal.extraction_method.

A "miss" is not a stored entity — it is the ABSENCE of an extracted signal.
Every candidate event that yields a signal gets an ``extracted_signal`` row, so a
miss is exactly a ``raw_signal_event`` with no matching ``extracted_signal``
(anti-join). Preflight on the dev DB confirmed ``unrecognized_signal`` rows ==
the anti-join set, so the table stored zero non-recomputable information and is
dropped. ``extraction_method`` is always ``DETERMINISTIC`` (the only extractor),
so the column and its CHECK are dropped too.

Revision ID: 0021_drop_unrecognized_and_extraction_method
Revises: 0020_prune_dead_schema
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0021_drop_unrecognized"
down_revision = "0020_prune_dead_schema"
branch_labels = None
depends_on = None

_EXTRACTION_METHOD_CHECK = "ck_extracted_signal_extraction_method"


def upgrade() -> None:
    op.drop_table("unrecognized_signal")
    op.drop_constraint(_EXTRACTION_METHOD_CHECK, "extracted_signal", type_="check")
    op.drop_column("extracted_signal", "extraction_method")


def downgrade() -> None:
    op.add_column(
        "extracted_signal",
        sa.Column(
            "extraction_method",
            sa.String(),
            nullable=False,
            server_default="DETERMINISTIC",
        ),
    )
    op.alter_column("extracted_signal", "extraction_method", server_default=None)
    op.create_check_constraint(
        _EXTRACTION_METHOD_CHECK,
        "extracted_signal",
        "extraction_method IN ('DETERMINISTIC')",
    )

    op.create_table(
        "unrecognized_signal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("attempted_methods", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="unrecognized_signal_pkey"),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["raw_signal_event.id"],
            name="fk_unrecognized_signal_event",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name="unrecognized_signal_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id", "event_id", name="uq_unrecognized_signal_user_event"
        ),
    )
    op.create_index(
        "ix_unrecognized_signal_user_event",
        "unrecognized_signal",
        ["user_id", "event_id"],
    )
