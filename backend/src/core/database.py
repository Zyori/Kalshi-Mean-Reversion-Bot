from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def create_engine(database_url: str):
    # SQLite is only used by the test suite (in-memory). Postgres is the
    # production driver and needs no special connect args.
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

    return create_async_engine(
        database_url,
        connect_args=connect_args,
        echo=False,
    )


def create_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
