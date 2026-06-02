"""
api/models/train_model.py  —  Pydantic request/response model for Train.

train_id is the only required field for creation.
All other fields are optional to support partial updates (PUT).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class TrainModel(BaseModel):
    train_id:       str                   = Field(..., description="Unique business identifier for the train")
    train_name:     Optional[str]         = Field(None, description="Human-readable train name")
    train_speed:    Optional[str]         = Field(None, description="Speed category: slow / fast / express")
    train_category: Optional[str]         = Field(None, description="Train type: freight / passenger / cargo")
    train_priority: Optional[str]         = Field(None, description="Priority: low / medium / high / critical")
    train_status:   Optional[str]         = Field(None, description="Status: pending / active / delayed / done")
    start_date:     Optional[str]         = Field(None, description="Departure date (YYYY-MM-DD)")
    start_time:     Optional[str]         = Field(None, description="Departure time (HH:MM)")
    due_date:       Optional[str]         = Field(None, description="Scheduled arrival date (YYYY-MM-DD)")
    due_time:       Optional[str]         = Field(None, description="Scheduled arrival time (HH:MM)")
    end_time:       Optional[str]         = Field(None, description="Actual arrival time (HH:MM)")
    alert_time:     Optional[str]         = Field(None, description="Alert trigger time (HH:MM)")
    alert_count:    Optional[int]         = Field(None, ge=0, description="Number of alerts sent")
    count:          Optional[int]         = Field(None, ge=0, description="General purpose counter")
    url:            Optional[str]         = Field(None, description="External reference URL")
    photo:          Optional[str]         = Field(None, description="Photo URL or path")
    check_url:      Optional[str]         = Field(None, description="Health-check URL")
    is_blocked:     Optional[bool]        = Field(None, description="Whether the train is blocked")
    task_id:        Optional[str]         = Field(None, description="Linked task identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "train_id": "TR-2024-001",
                "train_name": "Baku Express",
                "train_speed": "express",
                "train_category": "passenger",
                "train_priority": "high",
                "train_status": "pending",
                "start_date": "2024-06-01",
                "start_time": "08:00",
                "due_date": "2024-06-01",
                "due_time": "12:00",
                "is_blocked": False,
                "task_id": "TASK-42",
            }
        }