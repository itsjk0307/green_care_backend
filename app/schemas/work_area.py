from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkAreaResponse(BaseModel):
    id: UUID
    course_id: UUID
    name: str
    description: str | None
    zone_polygon: list[dict[str, Any]] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
