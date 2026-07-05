"""Drop the legacy label + regex-rule + drift tables and feed.verify_attempt.

The label->distill->verify loop and the regex-rule/drift extraction pipeline it
fed are gone (ADR 0016): mining is fully miner-based, so `filter_rule`,
`parser_rule`, `golden_label`, `filter_drift_warning`, and `parser_drift_warning`
are never written, `feed.verify_attempt` (loop-only) has no reader, and
`raw_signal_event.filter_rule_id` (rule-provenance) is always NULL. This drops the
dead schema so it matches the models everywhere. Data loss is accepted — these
tables/columns were dead-in-effect.

Forward-only: the schema is permanently retired (matches 0015's convention).

Revision ID: 0016_drop_legacy_rule_schema
Revises: 0015_drop_legacy_lab_tables
"""

import sqlalchemy as sa
from alembic import op

revision = "0016_drop_legacy_rule_schema"
down_revision = "0015_drop_legacy_lab_tables"
branch_labels = None
depends_on = None

# Child-before-parent (parser_drift_warning FKs golden_label). IF EXISTS + CASCADE
# makes each drop a no-op on databases that never carried these tables.
_DEAD_TABLES = (
    "filter_drift_warning",
    "parser_drift_warning",
    "golden_label",
    "filter_rule",
    "parser_rule",
)


def upgrade() -> None:
    for table in _DEAD_TABLES:
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE"))
    op.execute(sa.text("ALTER TABLE feed DROP COLUMN IF EXISTS verify_attempt"))
    op.execute(
        sa.text("ALTER TABLE raw_signal_event DROP COLUMN IF EXISTS filter_rule_id")
    )


def downgrade() -> None:
    raise NotImplementedError(
        "0016 drops the permanently-retired label/regex-rule/drift schema "
        "(ADR 0016); forward-only."
    )
