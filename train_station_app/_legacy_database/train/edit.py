"""
database/train/edit.py  —  TrainEditService

Responsible for UPDATE and DELETE operations on the trains table.
"""
from __future__ import annotations

from typing import Any

from database.session import DatabaseConnection


class TrainEditService:
    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    #  Update by _id                                                       #
    # ------------------------------------------------------------------ #

    def update_by_id(self, _id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """
        Partial update: only columns present in `data` are changed.
        Returns the updated row or None if _id not found.
        """
        if not data:
            return self._fetch_by_id(_id)

        # Build SET clause dynamically — only for columns that exist in schema
        allowed = {
            "train_name", "train_speed", "train_category", "train_priority",
            "train_status", "start_date", "start_time", "due_date", "due_time",
            "end_time", "alert_time", "alert_count", "count",
            "url", "photo", "check_url", "is_blocked", "task_id",
        }
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            return self._fetch_by_id(_id)

        set_clause = ", ".join(f"{col} = :{col}" for col in updates)
        updates["updated_at"] = "datetime('now')"
        set_clause += ", updated_at = datetime('now')"
        updates["_id"] = _id

        with self._db.cursor() as cur:
            cur.execute(
                f"UPDATE trains SET {set_clause} WHERE _id = :_id",
                updates,
            )
            if cur.rowcount == 0:
                return None
            cur.execute("SELECT * FROM trains WHERE _id = ?", (_id,))
            row = cur.fetchone()

        return dict(row) if row else None

    # ------------------------------------------------------------------ #
    #  Update by task_id                                                   #
    # ------------------------------------------------------------------ #

    def update_by_task_id(self, task_id: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Partial update for ALL trains linked to a task_id.
        Returns the list of updated rows.
        """
        allowed = {
            "train_name", "train_speed", "train_category", "train_priority",
            "train_status", "start_date", "start_time", "due_date", "due_time",
            "end_time", "alert_time", "alert_count", "count",
            "url", "photo", "check_url", "is_blocked",
        }
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            return self._fetch_by_task_id(task_id)

        set_clause = ", ".join(f"{col} = :{col}" for col in updates)
        set_clause += ", updated_at = datetime('now')"
        updates["task_id"] = task_id

        with self._db.cursor() as cur:
            cur.execute(
                f"UPDATE trains SET {set_clause} WHERE task_id = :task_id",
                updates,
            )

        return self._fetch_by_task_id(task_id)

    # ------------------------------------------------------------------ #
    #  Delete by _id                                                       #
    # ------------------------------------------------------------------ #

    def delete_by_id(self, _id: str) -> bool:
        """Delete a train by _id. Returns True if a row was deleted."""
        with self._db.cursor() as cur:
            cur.execute("DELETE FROM trains WHERE _id = ?", (_id,))
            return cur.rowcount > 0

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _fetch_by_id(self, _id: str) -> dict[str, Any] | None:
        with self._db.cursor() as cur:
            cur.execute("SELECT * FROM trains WHERE _id = ?", (_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    def _fetch_by_task_id(self, task_id: str) -> list[dict[str, Any]]:
        with self._db.cursor() as cur:
            cur.execute("SELECT * FROM trains WHERE task_id = ?", (task_id,))
            rows = cur.fetchall()
        return [dict(r) for r in rows]
