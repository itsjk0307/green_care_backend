from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


SeverityLevel = Literal["low", "moderate", "high", "critical"]


class AIResultResponse(BaseModel):
    disease_detected: bool
    disease_type: str | None = None
    confidence: float
    severity: SeverityLevel | None = None
    affected_area_percent: float | None = None
    bounding_boxes: dict[str, Any] | list[dict[str, Any]] | None = None
    recommendation: str | None = None
    model_version: str
    processed_at: datetime

    model_config = ConfigDict(from_attributes=True)

