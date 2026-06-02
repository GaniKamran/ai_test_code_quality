"""
database/train/model.py  —  SQLAlchemy ORM Model for Train

Maps directly to the `trains` table in the database.
Uses SQLAlchemy 2.x Mapped / mapped_column syntax for full type safety.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.session import Base  # single shared metadata registry


# ── UUID helper ────────────────────────────────────────────────────── #
def _uuid() -> str:
    return str(uuid.uuid4())


# ── ORM Model ─────────────────────────────────────────────────────── #
class Train(Base):
    """
    SQLAlchemy ORM model for the `trains` table.

    _id       → internal UUID primary key (never exposed to clients as-is)
    train_id  → external / business identifier (user-supplied or auto UUID)
    task_id   → optional foreign reference to a linked task
    """

    __tablename__ = "trains"

    # ── Keys ─────────────────────────────────────────────────────── #
    _id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid,
    )
    train_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, default=_uuid, index=True,
    )

    # ── Descriptive ──────────────────────────────────────────────── #
    train_name: Mapped[str | None]     = mapped_column(String(200), nullable=True)
    train_speed: Mapped[str | None]    = mapped_column(String(50),  nullable=True)
    train_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    train_priority: Mapped[str | None] = mapped_column(String(50),  nullable=True)
    train_status: Mapped[str]          = mapped_column(
        String(50), nullable=False, default="pending"
    )

    # ── Schedule ─────────────────────────────────────────────────── #
    start_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    start_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    due_date: Mapped[str | None]   = mapped_column(String(20), nullable=True)
    due_time: Mapped[str | None]   = mapped_column(String(10), nullable=True)
    end_time: Mapped[str | None]   = mapped_column(String(10), nullable=True)

    # ── Alerts ───────────────────────────────────────────────────── #
    alert_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    alert_count: Mapped[int]       = mapped_column(Integer, nullable=False, default=0)

    # ── Meta / references ────────────────────────────────────────── #
    count: Mapped[int]             = mapped_column(Integer, nullable=False, default=0)
    url: Mapped[str | None]        = mapped_column(Text, nullable=True)
    photo: Mapped[str | None]      = mapped_column(Text, nullable=True)
    check_url: Mapped[str | None]  = mapped_column(Text, nullable=True)
    is_blocked: Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    task_id: Mapped[str | None]    = mapped_column(String(100), nullable=True, index=True)

    # ── Audit ────────────────────────────────────────────────────── #
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # ── Helpers ──────────────────────────────────────────────────── #
    def __repr__(self) -> str:
        return (
            f"<Train _id={self._id!r} "
            f"train_id={self.train_id!r} "
            f"status={self.train_status!r}>"
        )

    def to_dict(self) -> dict:
        """Serialize all columns to a plain dict (safe for JSON response)."""
        result = {}
        for col in self.__mapper__.column_attrs:
            value = getattr(self, col.key)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[col.key] = value
        return result
