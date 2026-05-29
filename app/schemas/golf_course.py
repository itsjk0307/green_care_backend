from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GolfCourseCreate(BaseModel):
    name: str
    name_ko: str
    address: str
    address_ko: str
    total_area_sqm: float | None = None
    map_image_path: str | None = None


class GolfCourseUpdate(BaseModel):
    name: str | None = None
    name_ko: str | None = None
    address: str | None = None
    address_ko: str | None = None
    total_area_sqm: float | None = None
    is_active: bool | None = None


class GolfCourseResponse(BaseModel):
    id: UUID
    name: str
    name_ko: str
    address: str
    address_ko: str
    total_area_sqm: float | None
    map_image_path: str | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseMapUploadResponse(BaseModel):
    course_id: str
    map_url: str
    filename: str
