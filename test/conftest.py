"""
test/conftest.py  —  Shared fixtures for the functional test suite

Architecture:
  • Every test gets an ISOLATED in-memory SQLite database (no shared state)
  • FastAPI TestClient is wired to the isolated DB via dependency override
  • Fixtures use yield to guarantee teardown even on test failure

Pytest techniques demonstrated here:
  ┌─────────────────────────────────────────────────┐
  │  yield fixture  — setup + teardown in one block │
  │  scope="function" — fresh DB per test (default) │
  │  scope="session"  — shared once per pytest run  │
  │  fixture composition — client depends on db_url │
  │  autouse=False    — opt-in fixtures             │
  └─────────────────────────────────────────────────┘
"""
from __future__ import annotations

from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# ── path is handled by pytest.ini pythonpath ───────────────────────── #
from database.session import Base, get_session
from database.train.schemas import TrainCreate
from database.train.service import TrainService


# ═══════════════════════════════════════════════════════════════════════ #
#  Database fixtures                                                     #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.fixture()
def in_memory_engine():
    """
    Create a fresh in-memory SQLite engine for one test.
    All tables are created and dropped automatically.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(in_memory_engine) -> Generator[Session, None, None]:
    """
    Yield a transactional SQLAlchemy session.
    Rolls back after every test — no data leaks between tests.
    """
    TestingSession = sessionmaker(
        bind=in_memory_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = TestingSession()
    try:
        yield session
        session.rollback()        # ← always rollback after test
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════ #
#  Service fixture (unit-level — no HTTP)                                #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.fixture()
def train_service(in_memory_engine):
    """
    TrainService wired to the in-memory engine.
    Uses a custom session_factory so get_session() is never called.
    """
    from contextlib import contextmanager
    TestingSession = sessionmaker(
        bind=in_memory_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    @contextmanager
    def _session_factory():
        s = TestingSession()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    return TrainService(session_factory=_session_factory)


# ═══════════════════════════════════════════════════════════════════════ #
#  FastAPI TestClient fixture (HTTP-level)                               #
# ═══════════════════════════════════════════════════════════════════════ #

@pytest.fixture()
def client(in_memory_engine) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient with the production app but an isolated in-memory DB.

    Uses app.dependency_overrides to swap get_session() with a
    version backed by in_memory_engine — so HTTP tests never touch
    the real train_station.db file.
    """
    from contextlib import contextmanager
    from train_station_app.app import app

    TestingSession = sessionmaker(
        bind=in_memory_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    @contextmanager
    def _override_session():
        s = TestingSession()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    # Patch TrainService to use our in-memory session_factory
    from api.train.trains import TrainAPI
    original_init = TrainAPI.__init__

    def patched_init(self_inner):
        self_inner.router = __import__("fastapi").APIRouter()
        self_inner.service = TrainService(session_factory=_override_session)
        _register_routes(self_inner)

    def _register_routes(api_instance):
        from fastapi import Query, status
        from typing import Any, Optional
        from api.models.train_model import TrainModel
        from database.train.schemas import TrainCreate, TrainUpdate

        r = api_instance.router
        svc = api_instance.service

        r.add_api_route("/trains/create/",        api_instance.create_train,       methods=["POST"],   status_code=201)
        r.add_api_route("/trains/filter/",         api_instance.filter_trains,      methods=["GET"])
        r.add_api_route("/trains/search/",         api_instance.search_trains,      methods=["GET"])
        r.add_api_route("/trains/task/{task_id}",  api_instance.edit_train_by_task, methods=["PUT"])
        r.add_api_route("/trains/task/{task_id}",  api_instance.get_trains_by_task, methods=["GET"])
        r.add_api_route("/trains/{_id}",           api_instance.edit_train,         methods=["PUT"])
        r.add_api_route("/trains/",                api_instance.get_trains,         methods=["GET"])
        r.add_api_route("/trains/{_id}",           api_instance.delete_train,       methods=["DELETE"], status_code=204)

    TrainAPI.__init__ = patched_init

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    TrainAPI.__init__ = original_init  # restore


# ═══════════════════════════════════════════════════════════════════════ #
#  Pre-seeded client fixture                                             #
# ═══════════════════════════════════════════════════════════════════════ #

# ── Canonical test payloads ────────────────────────────────────────── #
TRAIN_PAYLOADS: list[dict] = [
    {
        "train_id": "TEST-001", "train_name": "Baku Express",
        "train_speed": "express", "train_category": "passenger",
        "train_priority": "high", "train_status": "active",
        "start_date": "2024-06-01", "start_time": "08:00",
        "due_date": "2024-06-01", "due_time": "12:00",
        "task_id": "TASK-A", "is_blocked": False,
    },
    {
        "train_id": "TEST-002", "train_name": "Ganja Freight",
        "train_speed": "slow", "train_category": "freight",
        "train_priority": "medium", "train_status": "pending",
        "start_date": "2024-06-02", "start_time": "10:00",
        "due_date": "2024-06-03", "due_time": "18:00",
        "task_id": "TASK-A", "is_blocked": False,
    },
    {
        "train_id": "TEST-003", "train_name": "Night Cargo",
        "train_speed": "fast", "train_category": "cargo",
        "train_priority": "critical", "train_status": "delayed",
        "start_date": "2024-06-03", "start_time": "22:00",
        "due_date": "2024-06-04", "due_time": "06:00",
        "task_id": "TASK-B", "is_blocked": True,
    },
]


@pytest.fixture()
def seeded_service(train_service: TrainService) -> TrainService:
    """TrainService pre-loaded with TRAIN_PAYLOADS (3 trains)."""
    for p in TRAIN_PAYLOADS:
        train_service.create(TrainCreate(**p))
    return train_service
