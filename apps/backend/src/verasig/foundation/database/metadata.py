"""Alembic metadata registry."""

from verasig.foundation.database.session import Base
from verasig.storage import models as _models  # noqa: F401

metadata = Base.metadata

__all__ = ["Base", "metadata"]
