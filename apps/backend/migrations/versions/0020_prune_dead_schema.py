"""Prune verified-dead schema.

Pre-launch cleanup: preflight on the dev DB confirmed
``extracted_signal.references_message_id`` is always NULL and
``raw_signal_event.matched_reasons`` has no business consumer, so both columns
are dropped. ``event_type`` is only ever ``NEW_ENTRY`` and ``extraction_method``
only ever ``DETERMINISTIC`` across all rows, so their CHECK constraints are
tightened to match the pruned ``SignalEventType``/``ExtractionMethod`` enums.

Revision ID: 0020_prune_dead_schema
Revises: 0019_mine_result
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0020_prune_dead_schema"
down_revision = "0019_mine_result"
branch_labels = None
depends_on = None

_EVENT_TYPE_CHECK = "ck_extracted_signal_event_type"
_EXTRACTION_METHOD_CHECK = "ck_extracted_signal_extraction_method"


def upgrade() -> None:
    op.drop_column("raw_signal_event", "matched_reasons")
    op.drop_column("extracted_signal", "references_message_id")

    op.drop_constraint(_EVENT_TYPE_CHECK, "extracted_signal", type_="check")
    op.create_check_constraint(
        _EVENT_TYPE_CHECK,
        "extracted_signal",
        "event_type IN ('NEW_ENTRY', 'MODIFY', 'CLOSE')",
    )

    op.drop_constraint(_EXTRACTION_METHOD_CHECK, "extracted_signal", type_="check")
    op.create_check_constraint(
        _EXTRACTION_METHOD_CHECK,
        "extracted_signal",
        "extraction_method IN ('DETERMINISTIC')",
    )


def downgrade() -> None:
    op.drop_constraint(_EXTRACTION_METHOD_CHECK, "extracted_signal", type_="check")
    op.create_check_constraint(
        _EXTRACTION_METHOD_CHECK,
        "extracted_signal",
        "extraction_method IN ('DETERMINISTIC', 'LLM_FALLBACK')",
    )

    op.drop_constraint(_EVENT_TYPE_CHECK, "extracted_signal", type_="check")
    op.create_check_constraint(
        _EVENT_TYPE_CHECK,
        "extracted_signal",
        "event_type IN ('NEW_ENTRY', 'MODIFY', 'CLOSE', 'UNRECOGNIZED')",
    )

    op.add_column(
        "extracted_signal",
        sa.Column("references_message_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "raw_signal_event",
        sa.Column("matched_reasons", JSONB(), nullable=False, server_default="[]"),
    )
    op.alter_column("raw_signal_event", "matched_reasons", server_default=None)
