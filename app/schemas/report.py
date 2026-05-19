from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.ai_result import AIResultResponse
from app.schemas.user import UserResponse

TaskType = Literal["disease_check", "irrigation", "fertilizing", "maintenance"]
ReportStatus = Literal["pending", "reviewed", "approved", "flagged"]
ReportStatusReviewOnly = Literal["reviewed", "approved", "flagged"]


class ReportCreate(BaseModel):
    task_type: TaskType
    latitude: float
    longitude: float
    location_name: str | None = None
    notes: str | None = None


class ReportResponse(BaseModel):
    id: UUID
    user_id: UUID
    task_type: TaskType
    latitude: float
    longitude: float
    location_name: str | None = None
    notes: str | None = None
    image_path: str
    status: ReportStatus
    created_at: datetime
    ai_result: AIResultResponse | None = None
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)


class ReportStatusUpdate(BaseModel):
    status: ReportStatusReviewOnly


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    total: int
    page: int
    limit: int

    model_config = ConfigDict(from_attributes=True)

