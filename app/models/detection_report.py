from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.ai_result import SeverityLevel


class DetectionUploadSource(str, enum.Enum):
    mobile = "mobile"
    web = "web"
    drone = "drone"


class DetectionCondition(str, enum.Enum):
    good = "good"
    disease_found = "disease_found"
    processing = "processing"


class DetectionReportStatus(str, enum.Enum):
    processing = "processing"
    completed = "completed"
    approved = "approved"
    flagged = "flagged"


class DetectionImageAngle(str, enum.Enum):
    top = "top"
    center = "center"
    bottom = "bottom"
    left = "left"
    right = "right"
    close_up = "close_up"


class DetectionReport(Base):
    __tablename__ = "detection_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("golf_courses.id"),
        nullable=False,
    )

    zone_coordinates: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    pin_x: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="X position as % of map image width 0-100",
    )
    pin_y: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Y position as % of map image height 0-100",
    )
    gps_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    upload_source: Mapped[DetectionUploadSource] = mapped_column(
        Enum(DetectionUploadSource, name="detection_upload_source"),
        nullable=False,
        default=DetectionUploadSource.mobile,
    )
    drone_height_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    condition: Mapped[DetectionCondition] = mapped_column(
        Enum(DetectionCondition, name="detection_condition"),
        nullable=False,
        default=DetectionCondition.processing,
    )
    disease_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[SeverityLevel | None] = mapped_column(
        Enum(SeverityLevel, name="severity_level", create_type=False),
        nullable=True,
    )
    affected_area_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommendation_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation_ko: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_model_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="mock-1.0.0",
    )

    status: Mapped[DetectionReportStatus] = mapped_column(
        Enum(DetectionReportStatus, name="detection_report_status"),
        nullable=False,
        default=DetectionReportStatus.processing,
    )

    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    uploader: Mapped["User"] = relationship(
        "User",
        foreign_keys=[uploaded_by],
        back_populates="uploaded_detection_reports",
    )
    course: Mapped["GolfCourse"] = relationship(
        "GolfCourse",
        foreign_keys=[course_id],
        back_populates="detection_reports",
    )
    reviewer: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[approved_by],
        back_populates="reviewed_detection_reports",
    )
    images: Mapped[list["DetectionImage"]] = relationship(
        "DetectionImage",
        back_populates="detection_report",
        cascade="all, delete-orphan",
        order_by="DetectionImage.image_path",
    )


class DetectionImage(Base):
    __tablename__ = "detection_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    detection_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("detection_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    angle: Mapped[DetectionImageAngle | None] = mapped_column(
        Enum(DetectionImageAngle, name="detection_image_angle"),
        nullable=True,
    )
    file_size_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    detection_report: Mapped["DetectionReport"] = relationship(
        "DetectionReport",
        back_populates="images",
    )
