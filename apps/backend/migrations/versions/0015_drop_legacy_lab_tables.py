"""Drop the retired lab-benchmark tables.

The six ``lab_*`` tables belong to the lab-benchmark feature (five migrations on
archive/lab-benchmark-runs-20260629) that template mining (ADR 0013) superseded.
Their creating migrations never reached develop, so fresh databases never have
these tables and this migration is a no-op there. Long-lived databases that once
ran the archived chain still carry them as orphans that no model or code
references; this removes them so the schema matches the models everywhere.

Forward-only: the tables are permanently retired (matches 0010's convention).

Revision ID: 0015_drop_legacy_lab_tables
Revises: 0014_user_fk_cascade
"""

import sqlalchemy as sa
from alembic import op

revision = "0015_drop_legacy_lab_tables"
down_revision = "0014_user_fk_cascade"
branch_labels = None
depends_on = None

# Every table the archived lab-benchmark chain created, child-before-parent.
# IF EXISTS + CASCADE makes each drop a no-op on databases that never had them.
_RETIRED_TABLES = (
    "lab_review_event",
    "lab_prediction",
    "lab_model_run",
    "lab_extraction_truth",
    "lab_provider_credential",
    "lab_benchmark_run",
)


def upgrade() -> None:
    for table in _RETIRED_TABLES:
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE"))


def downgrade() -> None:
    raise NotImplementedError(
        "0015 drops permanently-retired lab-benchmark tables (ADR 0013); forward-only."
    )
