from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

IssueTypeLiteral = Literal["disease", "equipment", "irrigation", "turf_damage", "other"]
PriorityLiteral = Literal["low", "medium", "high", "critical"]
StatusLiteral = Literal["open", "in_progress", "resolved"]


class IssueCreate(BaseModel):
    course_id: UUID
    issue_type: IssueTypeLiteral
    priority: PriorityLiteral = "medium"
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    pin_x: float = Field(..., ge=0.0, le=100.0)
    pin_y: float = Field(..., ge=0.0, le=100.0)
    hole_number: Optional[int] = Field(default=None, ge=1, le=18)
    assigned_to: Optional[UUID] = None


class IssueUpdateRequest(BaseModel):
    status: Optional[StatusLiteral] = None
    assigned_to: Optional[UUID] = None
    priority: Optional[PriorityLiteral] = None
    description: Optional[str] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)


class IssueResponse(BaseModel):
    id: UUID
    course_id: UUID
    issue_type: str
    priority: str
    title: str
    description: Optional[str] = None
    image_path: Optional[str] = None
    pin_x: float
    pin_y: float
    hole_number: Optional[int] = None
    status: str
    resolved_at: Optional[datetime] = None
    reported_by: UUID
    reporter_name: str
    assigned_to: Optional[UUID] = None
    assignee_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IssueMapResponse(BaseModel):
    id: UUID
    issue_type: str
    priority: str
    title: str
    pin_x: float
    pin_y: float
    status: str
    hole_number: Optional[int] = None
    reporter_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
