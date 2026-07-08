"""Upsert one owner-keyed row that stamps ``created_at``/``updated_at``.

The shared shape behind the per-owner config tables (parser_overlay, mine_result,
…): insert the row on first write, replace its value columns on conflict, and
keep ``created_at`` from the first write while advancing ``updated_at``.
"""

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session


def upsert_timestamped_row(
    session: Session, table, keys: dict, values: dict, now: datetime
) -> None:
    statement = pg_insert(table).values(
        **keys, **values, created_at=now, updated_at=now
    )
    statement = statement.on_conflict_do_update(
        index_elements=list(keys),
        set_={**values, "updated_at": now},
    )
    session.execute(statement)
    session.flush()
