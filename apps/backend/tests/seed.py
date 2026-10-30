"""Shared test seeding for the user-owned source/feed model.

Every `feed` carries a NOT NULL `source_id` cascading from a `source`, so a test
that seeds a feed directly must first own a source. `insert_source` upserts on
`(user_id, name)`, so it is safe to call once per user before `create_feed`.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from verasig.features.sources import source_repository

_INSTANT = datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)


def insert_source(
    session: Session,
    user_id: UUID,
    *,
    name: str = "Telegram",
    status: str = "connected",
) -> UUID:
    """Seed a source for `user_id` so its feeds satisfy `feed.source_id`."""
    return source_repository.create_source(
        session, user_id, name, status, {"phone": "+15551234567"}, _INSTANT
    ).id
