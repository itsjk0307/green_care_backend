from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WorkReportStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class MarkType(str, enum.Enum):
    pin = "pin"
    polygon = "polygon"


class WorkReport(Base):
    __tablename__ = "work_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("golf_courses.id"),
        nullable=False,
    )

    work_types: Mapped[list[str]] = mapped_column(JSONB, nullable=False)

    before_image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    after_image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    zone_coordinates: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    mark_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="How worker marked location: pin or polygon",
    )
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
    gps_route: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[WorkReportStatus] = mapped_column(
        Enum(WorkReportStatus, name="work_report_status"),
        nullable=False,
        default=WorkReportStatus.in_progress,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    worker: Mapped["User"] = relationship(
        "User",
        foreign_keys=[worker_id],
        back_populates="authored_work_reports",
    )
    course: Mapped["GolfCourse"] = relationship(
        "GolfCourse",
        foreign_keys=[course_id],
        back_populates="work_reports",
    )
    reviewer: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[approved_by],
        back_populates="reviewed_work_reports",
    )
