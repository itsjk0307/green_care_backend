from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.golf_course import GolfCourseResponse
from app.schemas.user import UserResponse

ALLOWED_WORK_TYPES: frozenset[str] = frozenset(
    {
        "mowing",
        "watering",
        "renovation",
        "fertilizing",
        "landscaping",
        "equipment",
        "top_dressing",
        "hole_setting",
        "snow_removal",
        "admin_work",
        "field_photo",
    }
)

WorkReportStatusLiteral = Literal[
    "in_progress",
    "completed",
    "pending",
    "approved",
    "rejected",
]

WorkReportReviewStatusLiteral = Literal["approved", "rejected"]


class WorkReportCreate(BaseModel):
    course_id: UUID
    work_types: list[str] = Field(..., min_length=1)
    zone_coordinates: list[dict[str, Any]] | None = None
    mark_type: str | None = None
    pin_x: float | None = None
    pin_y: float | None = None
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    notes: str | None = None

    @field_validator("work_types")
    @classmethod
    def validate_work_types(cls, values: list[str]) -> list[str]:
        invalid = [v for v in values if v not in ALLOWED_WORK_TYPES]
        if invalid:
            raise ValueError(
                f"Invalid work type(s): {invalid}. Allowed: {sorted(ALLOWED_WORK_TYPES)}"
            )
        return values


class WorkReportComplete(BaseModel):
    notes: str | None = None
    gps_route: list[dict[str, Any]] | None = None


class WorkReportStatusUpdate(BaseModel):
    status: WorkReportReviewStatusLiteral


class WorkReportResponse(BaseModel):
    id: UUID
    worker_id: UUID
    course_id: UUID
    work_types: list[str]
    before_image_path: str
    after_image_path: str | None
    zone_coordinates: list[dict[str, Any]] | None
    mark_type: str | None
    pin_x: float | None
    pin_y: float | None
    gps_latitude: float | None
    gps_longitude: float | None
    gps_route: list[dict[str, Any]] | None
    notes: str | None
    status: WorkReportStatusLiteral
    started_at: datetime
    completed_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime
    approved_by: UUID | None
    worker: UserResponse
    course: GolfCourseResponse

    model_config = ConfigDict(from_attributes=True)


class WorkReportListResponse(BaseModel):
    reports: list[WorkReportResponse]
    total: int
    page: int
    limit: int

    model_config = ConfigDict(from_attributes=True)


class FieldPhotoResponse(BaseModel):
    id: UUID
    worker_name: str
    gps_latitude: float | None
    gps_longitude: float | None
    image_url: str
    notes: str | None
    created_at: datetime
    status: WorkReportStatusLiteral

    model_config = ConfigDict(from_attributes=True)
