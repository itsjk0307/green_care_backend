from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    id: UUID
    type: str
    title_ko: str
    title_en: str
    body_ko: Optional[str] = None
    body_en: Optional[str] = None
    is_read: bool
    reference_id: Optional[UUID] = None
    reference_type: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnreadCountResponse(BaseModel):
    count: int


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total_count: int
    page: int
    per_page: int


class ReadAllResponse(BaseModel):
    count_updated: int
