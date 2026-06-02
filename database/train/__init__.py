"""
database/train/__init__.py

Public surface of the train database module.
Import from here — callers don't need to know the internal file layout.

    from database.train import TrainService, TrainCreate, TrainUpdate, TrainRead
"""
from database.train.model import Train
from database.train.schemas import TrainCreate, TrainPage, TrainRead, TrainUpdate
from database.train.repository import TrainRepository
from database.train.service import TrainService

__all__ = [
    "Train",
    "TrainCreate",
    "TrainUpdate",
    "TrainRead",
    "TrainPage",
    "TrainRepository",
    "TrainService",
]
