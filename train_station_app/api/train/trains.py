"""
api/train/trains.py  —  TrainAPI (SQLAlchemy)
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, status

from database.train.service import TrainService
from database.train.schemas import TrainCreate, TrainUpdate
from api.models.train_model import TrainModel


class TrainAPI:
    def __init__(self) -> None:
        self.router  = APIRouter()
        self.service = TrainService()

        self.router.add_api_route("/trains/create/",          self.create_train,       methods=["POST"],   status_code=status.HTTP_201_CREATED, summary="Create a new train")
        self.router.add_api_route("/trains/filter/",          self.filter_trains,      methods=["GET"],    summary="Filter trains")
        self.router.add_api_route("/trains/search/",          self.search_trains,      methods=["GET"],    summary="Search trains")
        self.router.add_api_route("/trains/task/{task_id}",   self.edit_train_by_task, methods=["PUT"],    summary="Bulk update by task_id")
        self.router.add_api_route("/trains/task/{task_id}",   self.get_trains_by_task, methods=["GET"],    summary="Get trains by task_id")
        self.router.add_api_route("/trains/{_id}",            self.edit_train,         methods=["PUT"],    summary="Update train by _id")
        self.router.add_api_route("/trains/",                 self.get_trains,         methods=["GET"],    summary="List trains")
        self.router.add_api_route("/trains/{_id}",            self.delete_train,       methods=["DELETE"], status_code=status.HTTP_204_NO_CONTENT, summary="Delete train")

    async def create_train(self, payload: TrainModel) -> dict[str, Any]:
        try:
            created = self.service.create(TrainCreate(**payload.model_dump(exclude_none=True)))
            return {"status": "created", "data": created}
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    async def get_trains(
        self,
        limit:  int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        return self.service.get_all(limit=limit, offset=offset)

    async def search_trains(
        self,
        q:     str = Query(..., min_length=1),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        try:
            return self.service.search(query=q, limit=limit)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    async def filter_trains(
        self,
        train_status:   Optional[str]  = Query(default=None),
        train_category: Optional[str]  = Query(default=None),
        train_priority: Optional[str]  = Query(default=None),
        train_speed:    Optional[str]  = Query(default=None),
        is_blocked:     Optional[bool] = Query(default=None),
        task_id:        Optional[str]  = Query(default=None),
        start_date:     Optional[str]  = Query(default=None),
        due_date:       Optional[str]  = Query(default=None),
        limit:  int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        return self.service.filter(
            train_status=train_status, train_category=train_category,
            train_priority=train_priority, train_speed=train_speed,
            is_blocked=is_blocked, task_id=task_id,
            start_date=start_date, due_date=due_date,
            limit=limit, offset=offset,
        )

    async def get_trains_by_task(self, task_id: str) -> dict[str, Any]:
        return self.service.get_by_task_id(task_id)

    async def edit_train(self, _id: str, payload: TrainModel) -> dict[str, Any]:
        try:
            updated = self.service.update(_id, TrainUpdate(**payload.model_dump(exclude_none=True)))
            return {"status": "updated", "data": updated}
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    async def edit_train_by_task(self, task_id: str, payload: TrainModel) -> dict[str, Any]:
        updated = self.service.update_by_task_id(task_id, TrainUpdate(**payload.model_dump(exclude_none=True)))
        return {"status": "updated", **updated}

    async def delete_train(self, _id: str) -> None:
        try:
            self.service.delete(_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
