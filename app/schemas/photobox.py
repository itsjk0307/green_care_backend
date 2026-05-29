from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PhotoItemResponse(BaseModel):
    id: UUID
    course_id: UUID
    work_types: list[str]
    notes: str | None = None
    before_image_path: str
    after_image_path: str | None = None
    hole_number: int | None = None
    worker_id: UUID
    worker_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PhotoListResponse(BaseModel):
    items: list[PhotoItemResponse]
    total_count: int
    page: int
    per_page: int


class HolePhotoSummaryResponse(BaseModel):
    hole_number: int
    photo_count: int
    last_photo_date: date | None = None
    latest_before_image: str | None = None
    latest_after_image: str | None = None

    model_config = ConfigDict(from_attributes=True)
