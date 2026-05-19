from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PlanStatusLiteral = Literal["draft", "published", "completed"]
ZoneStatusLiteral = Literal["pending", "in_progress", "done"]
AttendanceStatusLiteral = Literal["present", "absent", "overtime"]
ZoneTypeLiteral = Literal[
    "green",
    "tee",
    "fairway",
    "rough",
    "bunker",
    "landscaping",
    "other",
]


class DailyWorkPlanCreate(BaseModel):
    course_id: UUID
    plan_date: date
    weather: str
    temperature_min: float | None = None
    temperature_max: float | None = None
    rainfall_mm: float | None = None
    special_notes: str | None = None


class DailyWorkPlanUpdate(BaseModel):
    weather: str | None = None
    temperature_min: float | None = None
    temperature_max: float | None = None
    rainfall_mm: float | None = None
    special_notes: str | None = None
    status: PlanStatusLiteral | None = None


class DailyZoneTaskCreate(BaseModel):
    zone: ZoneTypeLiteral
    task_types: list[str] = Field(..., min_length=1)
    mowing_height_mm: float | None = None
    assigned_worker_ids: list[UUID] = Field(default_factory=list)
    notes: str | None = None


class DailyZoneTaskStatusUpdate(BaseModel):
    status: ZoneStatusLiteral


class DailyZoneTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    zone: str
    task_types: list[str]
    mowing_height_mm: float | None
    assigned_worker_ids: list[str]
    notes: str | None
    status: str
    completed_at: datetime | None


class DailyWorkerAttendanceItem(BaseModel):
    worker_id: UUID
    status: AttendanceStatusLiteral = "present"
    start_time: str | None = None
    end_time: str | None = None
    working_hours: float | None = None


class DailyWorkerAttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    worker_id: UUID
    status: str
    start_time: str | None
    end_time: str | None
    working_hours: float | None


class DailyWorkPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    course_id: UUID
    created_by: UUID
    plan_date: date
    weather: str
    temperature_min: float | None
    temperature_max: float | None
    rainfall_mm: float | None
    special_notes: str | None
    total_workers: int | None
    status: str
    created_at: datetime
    updated_at: datetime
    zone_tasks: list[DailyZoneTaskResponse] = Field(default_factory=list)
    attendance: list[DailyWorkerAttendanceResponse] = Field(default_factory=list)


class DailyWorkPlanListResponse(BaseModel):
    items: list[DailyWorkPlanResponse]
    total: int
