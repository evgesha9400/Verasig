from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Declarative base shared by all Verasig ORM models."""


def make_engine(url: str) -> Engine:
    return create_engine(url, future=True)


def make_session_factory(url: str) -> sessionmaker:
    return sessionmaker(bind=make_engine(url), future=True)
