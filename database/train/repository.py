"""
database/train/repository.py  —  Abstract Base + TrainRepository

Architecture:
  BaseRepository[T]  →  abstract generic CRUD (no SQL, only interface)
  TrainRepository    →  concrete SQLAlchemy implementation for Train

This separation lets you:
  • swap SQLite ↔ PostgreSQL without touching service code
  • mock BaseRepository in unit tests

Usage:
    with get_session() as db:
        repo = TrainRepository(db)
        train = repo.create(TrainCreate(train_name="Baku Express"))
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, Sequence, TypeVar

from sqlalchemy import or_, select, func
from sqlalchemy.orm import Session

from database.session import Base
from database.train.model import Train
from database.train.schemas import TrainCreate, TrainUpdate

T = TypeVar("T", bound=Base)


# ═══════════════════════════════════════════════════════════════════ #
#  Abstract Generic Repository                                        #
# ═══════════════════════════════════════════════════════════════════ #

class BaseRepository(ABC, Generic[T]):
    """
    Abstract CRUD contract.
    Every concrete repository implements these six operations.
    """

    @abstractmethod
    def create(self, data: Any) -> T: ...

    @abstractmethod
    def get_by_id(self, record_id: str) -> Optional[T]: ...

    @abstractmethod
    def get_all(self, limit: int, offset: int) -> Sequence[T]: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def update(self, record_id: str, data: Any) -> Optional[T]: ...

    @abstractmethod
    def delete(self, record_id: str) -> bool: ...


# ═══════════════════════════════════════════════════════════════════ #
#  Concrete Train Repository                                          #
# ═══════════════════════════════════════════════════════════════════ #

class TrainRepository(BaseRepository[Train]):
    """
    SQLAlchemy-backed repository for the `trains` table.

    All methods operate within the Session injected at construction.
    The caller (service layer) owns the transaction boundary.
    """

    def __init__(self, session: Session) -> None:
        self._db = session

    # ---------------------------------------------------------------- #
    #  CREATE                                                           #
    # ---------------------------------------------------------------- #

    def create(self, data: TrainCreate) -> Train:
        """
        Insert a new Train row.
        Generates _id and train_id (UUID) if not provided.
        """
        payload = data.model_dump(exclude_none=False)
        payload["_id"]      = str(uuid.uuid4())
        payload["train_id"] = payload.get("train_id") or str(uuid.uuid4())

        train = Train(**payload)
        self._db.add(train)
        self._db.flush()
        self._db.refresh(train)
        return train

    # ---------------------------------------------------------------- #
    #  READ — single                                                    #
    # ---------------------------------------------------------------- #

    def get_by_id(self, record_id: str) -> Optional[Train]:
        """Fetch by internal _id (UUID primary key)."""
        return self._db.get(Train, record_id)

    def get_by_train_id(self, train_id: str) -> Optional[Train]:
        """Fetch by external business train_id."""
        stmt = select(Train).where(Train.train_id == train_id)
        return self._db.scalars(stmt).first()

    def get_by_task_id(self, task_id: str) -> list[Train]:
        """Return all trains linked to a task_id."""
        stmt = (
            select(Train)
            .where(Train.task_id == task_id)
            .order_by(Train.created_at.desc())
        )
        return list(self._db.scalars(stmt).all())

    # ---------------------------------------------------------------- #
    #  READ — collection                                                #
    # ---------------------------------------------------------------- #

    def get_all(self, limit: int = 50, offset: int = 0) -> list[Train]:
        """Paginated fetch, ordered newest first."""
        stmt = (
            select(Train)
            .order_by(Train.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._db.scalars(stmt).all())

    def count(self) -> int:
        """Total number of trains in the table."""
        return self._db.scalar(select(func.count()).select_from(Train)) or 0

    # ---------------------------------------------------------------- #
    #  READ — search & filter                                           #
    # ---------------------------------------------------------------- #

    def search(self, query: str, limit: int = 50) -> list[Train]:
        """
        Case-insensitive LIKE search across:
          train_id, train_name, train_category, train_status
        """
        pattern = f"%{query}%"
        stmt = (
            select(Train)
            .where(
                or_(
                    Train.train_id.ilike(pattern),
                    Train.train_name.ilike(pattern),
                    Train.train_category.ilike(pattern),
                    Train.train_status.ilike(pattern),
                )
            )
            .order_by(Train.created_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt).all())

    def filter(
        self,
        train_status:   Optional[str]  = None,
        train_category: Optional[str]  = None,
        train_priority: Optional[str]  = None,
        train_speed:    Optional[str]  = None,
        is_blocked:     Optional[bool] = None,
        task_id:        Optional[str]  = None,
        start_date:     Optional[str]  = None,
        due_date:       Optional[str]  = None,
        limit:  int = 50,
        offset: int = 0,
    ) -> tuple[list[Train], int]:
        """
        Dynamic multi-column filter.
        Returns (rows, total_count) — caller wraps into TrainPage.
        Only non-None arguments are applied as WHERE clauses.
        """
        stmt = select(Train)

        if train_status   is not None: stmt = stmt.where(Train.train_status   == train_status)
        if train_category is not None: stmt = stmt.where(Train.train_category == train_category)
        if train_priority is not None: stmt = stmt.where(Train.train_priority == train_priority)
        if train_speed    is not None: stmt = stmt.where(Train.train_speed    == train_speed)
        if is_blocked     is not None: stmt = stmt.where(Train.is_blocked     == is_blocked)
        if task_id        is not None: stmt = stmt.where(Train.task_id        == task_id)
        if start_date     is not None: stmt = stmt.where(Train.start_date     >= start_date)
        if due_date       is not None: stmt = stmt.where(Train.due_date       <= due_date)

        # Count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = self._db.scalar(count_stmt) or 0

        stmt = stmt.order_by(Train.created_at.desc()).limit(limit).offset(offset)
        rows = list(self._db.scalars(stmt).all())

        return rows, total

    # ---------------------------------------------------------------- #
    #  UPDATE                                                           #
    # ---------------------------------------------------------------- #

    def update(self, record_id: str, data: TrainUpdate) -> Optional[Train]:
        """
        Partial update by _id.
        Only fields explicitly set in TrainUpdate (non-None) are written.
        Returns the updated Train or None if not found.
        """
        train = self.get_by_id(record_id)
        if train is None:
            return None

        updates = data.model_dump(exclude_none=True)
        valid_cols = {col.key for col in train.__mapper__.column_attrs}

        for field, value in updates.items():
            if field in valid_cols:
                setattr(train, field, value)

        self._db.flush()
        self._db.refresh(train)
        return train

    def update_by_task_id(self, task_id: str, data: TrainUpdate) -> list[Train]:
        """
        Bulk partial update for ALL trains linked to task_id.
        Returns the list of updated Train objects.
        """
        trains = self.get_by_task_id(task_id)
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return trains

        valid_cols = {col.key for col in Train.__mapper__.column_attrs}
        for train in trains:
            for field, value in updates.items():
                if field in valid_cols:
                    setattr(train, field, value)

        self._db.flush()
        for train in trains:
            self._db.refresh(train)
        return trains

    # ---------------------------------------------------------------- #
    #  DELETE                                                           #
    # ---------------------------------------------------------------- #

    def delete(self, record_id: str) -> bool:
        """
        Delete by _id.
        Returns True if a row was deleted, False if not found.
        """
        train = self.get_by_id(record_id)
        if train is None:
            return False
        self._db.delete(train)
        self._db.flush()
        return True
