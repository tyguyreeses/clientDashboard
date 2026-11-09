from __future__ import annotations

from datetime import datetime
import sqlite3

# Python 3.12+ deprecates sqlite3's implicit datetime adapter. Register an
# explicit ISO-8601 adapter so every SQLite engine, including test engines,
# binds authentication and business timestamps without the deprecation warning.
sqlite3.register_adapter(datetime, lambda value: value.isoformat(" "))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .settings import get_database_url


class Base(DeclarativeBase):
    pass


DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
    if engine.dialect.name != "sqlite":
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
