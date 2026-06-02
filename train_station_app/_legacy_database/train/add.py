"""
database/train/add.py  —  TrainAddService

Responsible for INSERT operations on the trains table.
"""
from __future__ import annotations

import uuid
from typing import Any

from database.session import DatabaseConnection


class TrainAddService:
    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def create_train(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Insert a new train record.
        Generates a UUID for _id if not provided.
        Returns the full created row as a dict.
        """
        _id = str(uuid.uuid4())
        train_id = data.get("train_id") or str(uuid.uuid4())

        with self._db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO trains (
                    _id, train_id, train_name, train_speed,
                    train_category, train_priority, train_status,
                    start_date, start_time, due_date, due_time,
                    end_time, alert_time, alert_count, count,
                    url, photo, check_url, is_blocked, task_id
                ) VALUES (
                    :_id, :train_id, :train_name, :train_speed,
                    :train_category, :train_priority, :train_status,
                    :start_date, :start_time, :due_date, :due_time,
                    :end_time, :alert_time, :alert_count, :count,
                    :url, :photo, :check_url, :is_blocked, :task_id
                )
                """,
                {
                    "_id": _id,
                    "train_id": train_id,
                    "train_name": data.get("train_name"),
                    "train_speed": data.get("train_speed"),
                    "train_category": data.get("train_category"),
                    "train_priority": data.get("train_priority"),
                    "train_status": data.get("train_status", "pending"),
                    "start_date": data.get("start_date"),
                    "start_time": data.get("start_time"),
                    "due_date": data.get("due_date"),
                    "due_time": data.get("due_time"),
                    "end_time": data.get("end_time"),
                    "alert_time": data.get("alert_time"),
                    "alert_count": data.get("alert_count", 0),
                    "count": data.get("count", 0),
                    "url": data.get("url"),
                    "photo": data.get("photo"),
                    "check_url": data.get("check_url"),
                    "is_blocked": int(data.get("is_blocked", False)),
                    "task_id": data.get("task_id"),
                },
            )
            cur.execute("SELECT * FROM trains WHERE _id = ?", (_id,))
            row = cur.fetchone()

        return dict(row)
