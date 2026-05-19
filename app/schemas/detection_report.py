from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.golf_course import GolfCourseResponse
from app.schemas.user import UserResponse

DetectionUploadSourceLiteral = Literal["mobile", "web", "drone"]
DetectionConditionLiteral = Literal["good", "disease_found", "processing"]
DetectionReportStatusLiteral = Literal["processing", "completed", "approved", "flagged"]
DetectionSeverityLiteral = Literal["low", "moderate", "high", "critical"]
DetectionImageAngleLiteral = Literal["top", "center", "bottom", "left", "right", "close_up"]


class DetectionCreate(BaseModel):
    course_id: UUID
    zone_coordinates: list[dict[str, Any]] | None = None
    pin_x: float | None = None
    pin_y: float | None = None
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    upload_source: DetectionUploadSourceLiteral
    drone_height_m: float | None = None


class DetectionImageResponse(BaseModel):
    id: UUID
    detection_report_id: UUID
    image_path: str
    angle: DetectionImageAngleLiteral | None
    file_size_mb: float | None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DetectionReportResponse(BaseModel):
    id: UUID
    uploaded_by: UUID
    course_id: UUID
    zone_coordinates: list[dict[str, Any]] | None
    pin_x: float | None
    pin_y: float | None
    gps_latitude: float | None
    gps_longitude: float | None
    upload_source: DetectionUploadSourceLiteral
    drone_height_m: float | None
    condition: DetectionConditionLiteral
    disease_type: str | None
    confidence: float | None
    severity: DetectionSeverityLiteral | None
    affected_area_percent: float | None
    recommendation_en: str | None
    recommendation_ko: str | None
    ai_model_version: str
    status: DetectionReportStatusLiteral
    processed_at: datetime | None
    created_at: datetime
    images: list[DetectionImageResponse]
    uploader: UserResponse
    course: GolfCourseResponse

    model_config = ConfigDict(from_attributes=True)


class DetectionListResponse(BaseModel):
    detections: list[DetectionReportResponse]
    total: int
    page: int
    limit: int

    model_config = ConfigDict(from_attributes=True)


class DetectionStatusUpdate(BaseModel):
    status: Literal["approved", "flagged"]
