"""
database/train/service.py  —  TrainService

Business-logic layer that sits between the API router and the repository.
Owns the transaction boundary via get_session() context manager.

Responsibilities:
  • Input validation (raises ValueError for bad data)
  • Calls repository inside a session context
  • Maps ORM objects → dicts (or Pydantic models) for the API layer
  • Raises HTTPException-friendly errors (404, 409)

Usage:
    service = TrainService()
    result  = service.create(TrainCreate(train_name="Baku Express"))
"""
from __future__ import annotations

from typing import Any, Optional

from database.session import get_session
from database.train.model import Train
from database.train.repository import TrainRepository
from database.train.schemas import TrainCreate, TrainPage, TrainRead, TrainUpdate


class TrainService:
    """
    Stateless service class — each method opens its own session.
    Designed for dependency injection: pass a custom session factory
    to override (useful in tests).
    """

    def __init__(self, session_factory=None) -> None:
        self._session_factory = session_factory or get_session

    # ── Private: session + repo context ───────────────────────────── #
    def _repo(self):
        """Return (session_cm, repo) — caller must use as context manager."""
        return self._session_factory

    # ---------------------------------------------------------------- #
    #  CREATE                                                           #
    # ---------------------------------------------------------------- #

    def create(self, data: TrainCreate) -> dict[str, Any]:
        """
        Create a new train.
        Raises ValueError if train_id already exists.
        """
        with self._session_factory() as db:
            repo = TrainRepository(db)

            # Uniqueness guard (train_id)
            if data.train_id and repo.get_by_train_id(data.train_id):
                raise ValueError(
                    f"Train with train_id='{data.train_id}' already exists."
                )

            train = repo.create(data)
            return train.to_dict()

    # ---------------------------------------------------------------- #
    #  READ — single                                                    #
    # ---------------------------------------------------------------- #

    def get_by_id(self, _id: str) -> dict[str, Any]:
        """
        Fetch a train by internal _id.
        Raises KeyError if not found.
        """
        with self._session_factory() as db:
            repo  = TrainRepository(db)
            train = repo.get_by_id(_id)
            if train is None:
                raise KeyError(f"Train with _id='{_id}' not found.")
            return train.to_dict()

    def get_by_train_id(self, train_id: str) -> dict[str, Any]:
        """Fetch by external business train_id. Raises KeyError if absent."""
        with self._session_factory() as db:
            repo  = TrainRepository(db)
            train = repo.get_by_train_id(train_id)
            if train is None:
                raise KeyError(f"Train with train_id='{train_id}' not found.")
            return train.to_dict()

    # ---------------------------------------------------------------- #
    #  READ — collection                                                #
    # ---------------------------------------------------------------- #

    def get_all(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """Paginated list of all trains."""
        with self._session_factory() as db:
            repo  = TrainRepository(db)
            rows  = repo.get_all(limit=limit, offset=offset)
            total = repo.count()
            return {
                "total":  total,
                "limit":  limit,
                "offset": offset,
                "data":   [t.to_dict() for t in rows],
            }

    def get_by_task_id(self, task_id: str) -> dict[str, Any]:
        """Return all trains linked to task_id."""
        with self._session_factory() as db:
            repo = TrainRepository(db)
            rows = repo.get_by_task_id(task_id)
            return {"total": len(rows), "data": [t.to_dict() for t in rows]}

    def search(self, query: str, limit: int = 50) -> dict[str, Any]:
        """Full-text search across train_id, name, category, status."""
        if not query.strip():
            raise ValueError("Search query must not be empty.")
        with self._session_factory() as db:
            repo = TrainRepository(db)
            rows = repo.search(query=query, limit=limit)
            return {"total": len(rows), "data": [t.to_dict() for t in rows]}

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
    ) -> dict[str, Any]:
        """Dynamic multi-column filter with pagination."""
        with self._session_factory() as db:
            repo = TrainRepository(db)
            rows, total = repo.filter(
                train_status=train_status,
                train_category=train_category,
                train_priority=train_priority,
                train_speed=train_speed,
                is_blocked=is_blocked,
                task_id=task_id,
                start_date=start_date,
                due_date=due_date,
                limit=limit,
                offset=offset,
            )
            return {
                "total":  total,
                "limit":  limit,
                "offset": offset,
                "data":   [t.to_dict() for t in rows],
            }

    # ---------------------------------------------------------------- #
    #  UPDATE                                                           #
    # ---------------------------------------------------------------- #

    def update(self, _id: str, data: TrainUpdate) -> dict[str, Any]:
        """
        Partial update by _id.
        Raises KeyError if not found.
        """
        with self._session_factory() as db:
            repo    = TrainRepository(db)
            updated = repo.update(_id, data)
            if updated is None:
                raise KeyError(f"Train with _id='{_id}' not found.")
            return updated.to_dict()

    def update_by_task_id(self, task_id: str, data: TrainUpdate) -> dict[str, Any]:
        """Bulk partial update for all trains linked to task_id."""
        with self._session_factory() as db:
            repo    = TrainRepository(db)
            updated = repo.update_by_task_id(task_id, data)
            return {
                "count": len(updated),
                "data":  [t.to_dict() for t in updated],
            }

    # ---------------------------------------------------------------- #
    #  DELETE                                                           #
    # ---------------------------------------------------------------- #

    def delete(self, _id: str) -> None:
        """
        Delete by _id.
        Raises KeyError if not found.
        """
        with self._session_factory() as db:
            repo    = TrainRepository(db)
            deleted = repo.delete(_id)
            if not deleted:
                raise KeyError(f"Train with _id='{_id}' not found.")
