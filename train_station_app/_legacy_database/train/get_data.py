"""
database/train/get_data.py  —  TrainQueryService

Responsible for all SELECT / READ operations on the trains table.
"""
from __future__ import annotations

from typing import Any

from database.session import DatabaseConnection


class TrainQueryService:
    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    #  Get all (paginated)                                                 #
    # ------------------------------------------------------------------ #

    def get_all(
        self,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        desc: bool = True,
    ) -> dict[str, Any]:
        """
        Return a page of trains together with total count.

        Returns:
            {
                "total": int,
                "limit": int,
                "offset": int,
                "data": [...]
            }
        """
        direction = "DESC" if desc else "ASC"
        safe_cols = {
            "created_at", "updated_at", "train_name", "train_priority",
            "train_status", "train_speed", "due_date",
        }
        if order_by not in safe_cols:
            order_by = "created_at"

        with self._db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM trains")
            total = cur.fetchone()[0]

            cur.execute(
                f"SELECT * FROM trains ORDER BY {order_by} {direction} LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = cur.fetchall()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": [dict(r) for r in rows],
        }

    # ------------------------------------------------------------------ #
    #  Get by _id                                                          #
    # ------------------------------------------------------------------ #

    def get_by_id(self, _id: str) -> dict[str, Any] | None:
        with self._db.cursor() as cur:
            cur.execute("SELECT * FROM trains WHERE _id = ?", (_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------ #
    #  Get by task_id                                                      #
    # ------------------------------------------------------------------ #

    def get_by_task_id(self, task_id: str) -> list[dict[str, Any]]:
        with self._db.cursor() as cur:
            cur.execute(
                "SELECT * FROM trains WHERE task_id = ? ORDER BY created_at DESC",
                (task_id,),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    #  Search (prefix + full-text across key columns)                     #
    # ------------------------------------------------------------------ #

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """
        Case-insensitive LIKE search across train_id, train_name,
        train_category and train_status.
        """
        pattern = f"%{query}%"
        with self._db.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM trains
                WHERE  train_id       LIKE :q COLLATE NOCASE
                    OR train_name     LIKE :q COLLATE NOCASE
                    OR train_category LIKE :q COLLATE NOCASE
                    OR train_status   LIKE :q COLLATE NOCASE
                ORDER BY created_at DESC
                LIMIT :lim
                """,
                {"q": pattern, "lim": limit},
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
