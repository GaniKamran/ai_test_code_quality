"""
database/train/filter.py  —  TrainFilterService

Dynamic multi-column filtering with optional pagination.
All filter parameters are optional — only non-None values are applied.
"""
from __future__ import annotations

from typing import Any, Optional

from database.session import DatabaseConnection


class TrainFilterService:
    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def filter(
        self,
        train_status: Optional[str] = None,
        train_category: Optional[str] = None,
        train_priority: Optional[str] = None,
        train_speed: Optional[str] = None,
        is_blocked: Optional[bool] = None,
        task_id: Optional[str] = None,
        start_date: Optional[str] = None,
        due_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Filter trains by any combination of the supported columns.

        Date fields accept ISO-8601 strings (YYYY-MM-DD).
        Returns paginated result with total count.
        """
        conditions: list[str] = []
        params: dict[str, Any] = {}

        if train_status is not None:
            conditions.append("train_status = :train_status")
            params["train_status"] = train_status

        if train_category is not None:
            conditions.append("train_category = :train_category")
            params["train_category"] = train_category

        if train_priority is not None:
            conditions.append("train_priority = :train_priority")
            params["train_priority"] = train_priority

        if train_speed is not None:
            conditions.append("train_speed = :train_speed")
            params["train_speed"] = train_speed

        if is_blocked is not None:
            conditions.append("is_blocked = :is_blocked")
            params["is_blocked"] = int(is_blocked)

        if task_id is not None:
            conditions.append("task_id = :task_id")
            params["task_id"] = task_id

        if start_date is not None:
            conditions.append("start_date >= :start_date")
            params["start_date"] = start_date

        if due_date is not None:
            conditions.append("due_date <= :due_date")
            params["due_date"] = due_date

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with self._db.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM trains {where_clause}", params)
            total = cur.fetchone()[0]

            params["limit"] = limit
            params["offset"] = offset
            cur.execute(
                f"""
                SELECT * FROM trains
                {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """,
                params,
            )
            rows = cur.fetchall()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": [dict(r) for r in rows],
        }
