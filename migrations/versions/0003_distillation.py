"""candidate events, extraction outputs, distilled rules, golden corpus, drift.

Slice 3/4: raw_signal_event, extracted_signal, unrecognized_signal, filter_rule,
parser_rule, golden_label, filter_drift_warning. Append-only; JSONB mirrors the
list/map contract fields + GoldenLabel.expected.

Revision ID: 0003_distillation
Revises: 0002_raw_capture
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_distillation"
down_revision = "0002_raw_capture"
branch_labels = None
depends_on = None

_CHANNEL_FK = "telegram_channel.channel_id"
_EVENT_FK = "raw_signal_event.id"


def upgrade() -> None:
    op.create_table(
        "raw_signal_event",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "channel_id", sa.BigInteger(), sa.ForeignKey(_CHANNEL_FK), nullable=False
        ),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("candidate_text", sa.Text(), nullable=False),
        sa.Column("materialized_by", sa.String(), nullable=False),
        sa.Column("matched_reasons", postgresql.JSONB(), nullable=False),
        sa.Column("filter_rule_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("channel_id", "message_id", name="uq_raw_signal_event_msg"),
    )
    op.create_table(
        "extracted_signal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey(_EVENT_FK), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("references_message_id", sa.BigInteger(), nullable=True),
        sa.Column("entry_type", sa.String(), nullable=True),
        sa.Column("entry_low", sa.Numeric(), nullable=True),
        sa.Column("entry_high", sa.Numeric(), nullable=True),
        sa.Column("stop_loss", sa.Numeric(), nullable=True),
        sa.Column("take_profits", postgresql.JSONB(), nullable=False),
        sa.Column("leverage", sa.Numeric(), nullable=True),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("extraction_method", sa.String(), nullable=False),
        sa.Column("rule_id", sa.String(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "unrecognized_signal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey(_EVENT_FK), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("attempted_methods", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "filter_rule",
        sa.Column("rule_id", sa.String(), primary_key=True),
        sa.Column(
            "channel_id", sa.BigInteger(), sa.ForeignKey(_CHANNEL_FK), nullable=True
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("include_patterns", postgresql.JSONB(), nullable=False),
        sa.Column("exclude_patterns", postgresql.JSONB(), nullable=False),
        sa.Column("matched_reason_template", sa.String(), nullable=False),
        sa.Column("recall_target", sa.Float(), nullable=False),
        sa.Column("python_filter", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("distilled_from_label_ids", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "parser_rule",
        sa.Column("rule_id", sa.String(), primary_key=True),
        sa.Column(
            "channel_id", sa.BigInteger(), sa.ForeignKey(_CHANNEL_FK), nullable=True
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("patterns", postgresql.JSONB(), nullable=False),
        sa.Column("field_map", postgresql.JSONB(), nullable=False),
        sa.Column("side_aliases", postgresql.JSONB(), nullable=False),
        sa.Column("python_extractor", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("distilled_from_label_ids", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "golden_label",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "channel_id", sa.BigInteger(), sa.ForeignKey(_CHANNEL_FK), nullable=False
        ),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("is_signal", sa.Boolean(), nullable=False),
        sa.Column("expected", postgresql.JSONB(), nullable=True),
        sa.Column("labeled_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("channel_id", "message_id", name="uq_golden_label_msg"),
    )
    op.create_table(
        "filter_drift_warning",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "channel_id", sa.BigInteger(), sa.ForeignKey(_CHANNEL_FK), nullable=False
        ),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("filter_rule_version", sa.Integer(), nullable=True),
        sa.Column("miss_discovered_by", sa.String(), nullable=False),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey(_EVENT_FK), nullable=True),
        sa.Column(
            "source_label_id",
            sa.Uuid(),
            sa.ForeignKey("golden_label.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("channel_id", "message_id", name="uq_filter_drift_msg"),
    )


def downgrade() -> None:
    op.drop_table("filter_drift_warning")
    op.drop_table("golden_label")
    op.drop_table("parser_rule")
    op.drop_table("filter_rule")
    op.drop_table("unrecognized_signal")
    op.drop_table("extracted_signal")
    op.drop_table("raw_signal_event")
