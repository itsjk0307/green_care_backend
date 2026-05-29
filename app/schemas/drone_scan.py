from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScanResultResponse(BaseModel):
    id: UUID
    scan_id: UUID
    hole_number: int
    disease_type: str
    confidence: float
    severity: Optional[str] = None
    affected_area_pct: Optional[float] = None
    bbox_x: Optional[float] = None
    bbox_y: Optional[float] = None
    bbox_width: Optional[float] = None
    bbox_height: Optional[float] = None
    recommendation_ko: Optional[str] = None
    recommendation_en: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DroneScanCreate(BaseModel):
    course_id: UUID
    scan_date: date
    notes: Optional[str] = None


class DroneScanResponse(BaseModel):
    id: UUID
    course_id: UUID
    uploaded_by: UUID
    scan_date: date
    image_path: str
    image_width: int
    image_height: int
    status: str
    notes: Optional[str] = None
    created_at: datetime
    result_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DroneScanDetailResponse(BaseModel):
    id: UUID
    course_id: UUID
    uploaded_by: UUID
    scan_date: date
    image_path: str
    image_width: int
    image_height: int
    status: str
    notes: Optional[str] = None
    created_at: datetime
    result_count: int = 0
    results: list[ScanResultResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
