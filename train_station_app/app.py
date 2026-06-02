"""
train_station_app/app.py  —  FastAPI Application entry point
Uses SQLAlchemy TrainService via database/ package.
"""
from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from database.session import Base, engine
from api.train.trains import TrainAPI


def _create_tables() -> None:
    Base.metadata.create_all(bind=engine)


class Application:
    def __init__(self) -> None:
        self.app = FastAPI(
            title="Train Station API",
            description="Full CRUD API for managing train schedules. Powered by FastAPI + SQLAlchemy.",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )
        _create_tables()
        self._register_apis()
        self._register_health()

    def _register_apis(self) -> None:
        train_api = TrainAPI()
        self.app.include_router(train_api.router, tags=["Train"])

    def _register_health(self) -> None:
        @self.app.get("/", tags=["Health"])
        async def health_check():
            return {"status": "ok", "service": "Train Station API", "version": "1.0.0"}


_instance = Application()
app = _instance.app

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
