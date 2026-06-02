"""
database/train/schemas.py  —  Pydantic Schemas for Train

Separates the API contract (Pydantic) from the DB layer (SQLAlchemy).

Three schemas follow the standard pattern:
  TrainCreate  — fields accepted on POST  (train_id optional)
  TrainUpdate  — all fields optional      (for PATCH / partial PUT)
  TrainRead    — full response schema     (includes _id, timestamps)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Create ─────────────────────────────────────────────────────────── #
class TrainCreate(BaseModel):
    """
    Payload for creating a new train.
    train_id is optional — the repository assigns a UUID if omitted.
    """
    train_id:       Optional[str]  = Field(None,  description="Business ID (UUID auto-assigned if blank)")
    train_name:     Optional[str]  = Field(None,  description="Human-readable train name")
    train_speed:    Optional[str]  = Field(None,  description="slow | fast | express")
    train_category: Optional[str]  = Field(None,  description="passenger | freight | cargo")
    train_priority: Optional[str]  = Field(None,  description="low | medium | high | critical")
    train_status:   Optional[str]  = Field("pending", description="pending | active | delayed | done")
    start_date:     Optional[str]  = Field(None,  description="YYYY-MM-DD")
    start_time:     Optional[str]  = Field(None,  description="HH:MM")
    due_date:       Optional[str]  = Field(None,  description="YYYY-MM-DD")
    due_time:       Optional[str]  = Field(None,  description="HH:MM")
    end_time:       Optional[str]  = Field(None,  description="HH:MM")
    alert_time:     Optional[str]  = Field(None,  description="HH:MM")
    alert_count:    Optional[int]  = Field(0,     ge=0)
    count:          Optional[int]  = Field(0,     ge=0)
    url:            Optional[str]  = Field(None)
    photo:          Optional[str]  = Field(None)
    check_url:      Optional[str]  = Field(None)
    is_blocked:     Optional[bool] = Field(False)
    task_id:        Optional[str]  = Field(None,  description="Linked task identifier")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "train_name": "Baku Express",
                "train_speed": "express",
                "train_category": "passenger",
                "train_priority": "high",
                "train_status": "pending",
                "start_date": "2024-06-01",
                "start_time": "08:00",
                "due_date": "2024-06-01",
                "due_time": "12:00",
                "task_id": "TASK-42",
            }
        }
    )


# ── Update (partial) ───────────────────────────────────────────────── #
class TrainUpdate(BaseModel):
    """
    Payload for updating an existing train (all fields optional).
    Only non-None fields are written to the database.
    """
    train_name:     Optional[str]  = None
    train_speed:    Optional[str]  = None
    train_category: Optional[str]  = None
    train_priority: Optional[str]  = None
    train_status:   Optional[str]  = None
    start_date:     Optional[str]  = None
    start_time:     Optional[str]  = None
    due_date:       Optional[str]  = None
    due_time:       Optional[str]  = None
    end_time:       Optional[str]  = None
    alert_time:     Optional[str]  = None
    alert_count:    Optional[int]  = None
    count:          Optional[int]  = None
    url:            Optional[str]  = None
    photo:          Optional[str]  = None
    check_url:      Optional[str]  = None
    is_blocked:     Optional[bool] = None
    task_id:        Optional[str]  = None


# ── Read (response) ────────────────────────────────────────────────── #
class TrainRead(BaseModel):
    """
    Full response schema returned to the client.
    Includes internal _id and audit timestamps.
    """
    _id:            str
    train_id:       str
    train_name:     Optional[str]  = None
    train_speed:    Optional[str]  = None
    train_category: Optional[str]  = None
    train_priority: Optional[str]  = None
    train_status:   str
    start_date:     Optional[str]  = None
    start_time:     Optional[str]  = None
    due_date:       Optional[str]  = None
    due_time:       Optional[str]  = None
    end_time:       Optional[str]  = None
    alert_time:     Optional[str]  = None
    alert_count:    int
    count:          int
    url:            Optional[str]  = None
    photo:          Optional[str]  = None
    check_url:      Optional[str]  = None
    is_blocked:     bool
    task_id:        Optional[str]  = None
    created_at:     Optional[datetime] = None
    updated_at:     Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Paginated wrapper ──────────────────────────────────────────────── #
class TrainPage(BaseModel):
    """Standard paginated response envelope."""
    total:  int
    limit:  int
    offset: int
    data:   list[TrainRead]
