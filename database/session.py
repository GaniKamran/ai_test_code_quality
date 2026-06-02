"""
database/session.py  —  SQLAlchemy engine & session factory

Single source of truth for all DB connectivity.
Uses SQLite by default; swap DATABASE_URL env var for PostgreSQL/MySQL.

Usage:
    from database.session import get_session, engine
    with get_session() as session:
        session.add(obj)
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker


# ── Connection URL ────────────────────────────────────────────────── #
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "sqlite:///./train_station.db",
)

# ── Base (for create_all convenience) ───────────────────────────── #
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Declarative base — import from here to keep one metadata registry."""
    pass


# ── Engine ────────────────────────────────────────────────────────── #
_connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=False,          # set True for SQL debug logging
    future=True,
)

# Enable WAL mode + FK enforcement for SQLite
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _connection_record) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


# ── Session factory ───────────────────────────────────────────────── #
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── Context-manager helper ────────────────────────────────────────── #
@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Yield a transactional Session that auto-commits on success
    and rolls back on any exception.

    Example:
        with get_session() as db:
            db.add(train)
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
