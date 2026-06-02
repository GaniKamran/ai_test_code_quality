"""
database/session.py

SQLite database connection manager.
Uses a context-manager pattern so every caller gets a clean cursor
and commits/rolls back automatically.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Generator


DB_PATH = "train_station.db"


class DatabaseConnection:
    """
    Thin wrapper around sqlite3.  Keeps a single persistent connection
    and exposes a context-manager cursor for transactional work.

    Usage:
        db = DatabaseConnection()
        with db.cursor() as cur:
            cur.execute("SELECT ...")
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection = sqlite3.connect(
            db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema()

    # ------------------------------------------------------------------ #
    #  Schema bootstrap                                                    #
    # ------------------------------------------------------------------ #

    def _init_schema(self) -> None:
        """Create the trains table if it doesn't exist yet."""
        with self.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS trains (
                    _id             TEXT PRIMARY KEY,
                    train_id        TEXT NOT NULL UNIQUE,
                    train_name      TEXT,
                    train_speed     TEXT,
                    train_category  TEXT,
                    train_priority  TEXT,
                    train_status    TEXT DEFAULT 'pending',
                    start_date      TEXT,
                    start_time      TEXT,
                    due_date        TEXT,
                    due_time        TEXT,
                    end_time        TEXT,
                    alert_time      TEXT,
                    alert_count     INTEGER DEFAULT 0,
                    count           INTEGER DEFAULT 0,
                    url             TEXT,
                    photo           TEXT,
                    check_url       TEXT,
                    is_blocked      INTEGER DEFAULT 0,
                    task_id         TEXT,
                    created_at      TEXT DEFAULT (datetime('now')),
                    updated_at      TEXT DEFAULT (datetime('now'))
                )
                """
            )

    # ------------------------------------------------------------------ #
    #  Context manager                                                     #
    # ------------------------------------------------------------------ #

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cur.close()

    def close(self) -> None:
        self._conn.close()
