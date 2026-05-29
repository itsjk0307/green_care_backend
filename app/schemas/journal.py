from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WeatherInfoResponse(BaseModel):
    weather: str | None = None
    temperature_min: float | None = None
    temperature_max: float | None = None
    rainfall_mm: float | None = None
    special_notes: str | None = None
    status: str | None = None
    total_workers: int | None = None
    plan_exists: bool = False


class AttendanceItemResponse(BaseModel):
    worker_name: str
    status: str
    start_time: str | None = None
    end_time: str | None = None
    working_hours: float | None = None


class AttendanceSummaryResponse(BaseModel):
    total_present: int = 0
    total_absent: int = 0
    total_overtime: int = 0


class AttendanceSectionResponse(BaseModel):
    items: list[AttendanceItemResponse] = Field(default_factory=list)
    summary: AttendanceSummaryResponse = Field(default_factory=AttendanceSummaryResponse)


class ZoneTaskJournalItemResponse(BaseModel):
    zone: str
    task_types: list[str]
    mowing_height_mm: float | None = None
    status: str
    completed_at: datetime | None = None
    assigned_worker_names: list[str] = Field(default_factory=list)


class DailyJournalResponse(BaseModel):
    course_id: UUID
    journal_date: date
    weather_info: WeatherInfoResponse
    attendance: AttendanceSectionResponse
    zone_tasks: list[ZoneTaskJournalItemResponse] = Field(default_factory=list)
    photo_count: int = 0
    issues_opened: int = 0
    issues_resolved: int = 0


class MonthlyDaySummaryResponse(BaseModel):
    date: date
    plan_exists: bool
    completion_pct: float | None = None
    worker_count: int | None = None
    weather: str | None = None


class MonthlyJournalResponse(BaseModel):
    course_id: UUID
    month: str
    days: list[MonthlyDaySummaryResponse] = Field(default_factory=list)


class JournalExportRequest(BaseModel):
    course_id: UUID
    from_date: date
    to_date: date
    format: str = "excel"

    model_config = ConfigDict(extra="forbid")
