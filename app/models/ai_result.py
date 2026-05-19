from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SeverityLevel(str, enum.Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    critical = "critical"


class AIResult(Base):
    __tablename__ = "ai_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id"),
        nullable=False,
        unique=True,
    )
    disease_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    disease_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[SeverityLevel | None] = mapped_column(
        Enum(SeverityLevel, name="severity_level"),
        nullable=True,
    )
    affected_area_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    bounding_boxes: Mapped[dict[str, Any] | list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    report: Mapped["Report"] = relationship(
        "Report",
        back_populates="ai_result",
    )

