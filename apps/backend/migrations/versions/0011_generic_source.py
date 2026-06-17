"""Generic per-user `source` (connection) replacing `user_telegram_link`.

Introduces a provider-agnostic `source` row (a user's connection to a provider;
Telegram is the only `name` allowed today) and roots every `feed` at it via
`feed.source_id` ON DELETE CASCADE, so disconnecting a source purges all of its
feeds and their captured history.

Each `user_telegram_link` becomes one `source` (`name='Telegram'`), carrying its
`status` and folding its connection secrets into `config_encrypted` (a JSON object
that embeds the *existing* per-field envelopes verbatim, preserving their AES-GCM
ciphertext + AAD so nothing is re-encrypted). `user_telegram_link` is then dropped.

Revision ID: 0011_generic_source
Revises: 0010_user_owned_feed
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0011_generic_source"
down_revision = "0010_user_owned_feed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("config_encrypted", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="source_pkey"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name="fk_source_user",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_id", "name", name="uq_source_user_name"),
        sa.CheckConstraint("name IN ('Telegram')", name="ck_source_name"),
        sa.CheckConstraint(
            "status IN ('pending', 'connected')", name="ck_source_status"
        ),
    )

    # one source per telegram link; fold the connection secrets into config_encrypted,
    # embedding the existing encrypted envelopes verbatim (no re-encryption).
    op.execute(
        sa.text(
            "INSERT INTO source "
            "(id, user_id, name, status, config_encrypted, created_at, updated_at) "
            "SELECT gen_random_uuid(), user_id, 'Telegram', status, "
            "jsonb_build_object("
            "'api_id', api_id, "
            "'api_hash_encrypted', api_hash_encrypted, "
            "'phone', phone, "
            "'session_string_encrypted', session_string_encrypted, "
            "'phone_code_hash', phone_code_hash"
            "), updated_at, updated_at "
            "FROM user_telegram_link"
        )
    )
    op.drop_table("user_telegram_link")

    op.add_column("feed", sa.Column("source_id", sa.Uuid(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE feed f SET source_id = s.id "
            "FROM source s WHERE s.user_id = f.user_id AND s.name = 'Telegram'"
        )
    )
    op.create_foreign_key(
        "fk_feed_source",
        "feed",
        "source",
        ["source_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("feed", "source_id", existing_type=sa.Uuid(), nullable=False)


def downgrade() -> None:
    raise NotImplementedError(
        "0011 folds user_telegram_link into source; forward-only."
    )
