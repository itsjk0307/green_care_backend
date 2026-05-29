from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DroneScan(Base):
    __tablename__ = "drone_scans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded', 'processing', 'completed', 'failed')",
            name="drone_scans_status_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("golf_courses.id"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    scan_date: Mapped[date] = mapped_column(Date, nullable=False)
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    image_width: Mapped[int] = mapped_column(Integer, nullable=False)
    image_height: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="uploaded",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    course: Mapped["GolfCourse"] = relationship(
        "GolfCourse",
        back_populates="drone_scans",
        foreign_keys=[course_id],
    )
    uploader: Mapped["User"] = relationship(
        "User",
        back_populates="uploaded_drone_scans",
        foreign_keys=[uploaded_by],
    )
    results: Mapped[list["ScanResult"]] = relationship(
        "ScanResult",
        back_populates="scan",
        cascade="all, delete-orphan",
        order_by="ScanResult.hole_number",
        lazy="selectin",
    )


class ScanResult(Base):
    __tablename__ = "scan_results"
    __table_args__ = (
        CheckConstraint(
            "hole_number BETWEEN 1 AND 18",
            name="hole_number_range",
        ),
        CheckConstraint(
            "confidence BETWEEN 0.0 AND 1.0",
            name="confidence_range",
        ),
        CheckConstraint(
            "severity IS NULL OR severity IN ('low', 'medium', 'high', 'critical')",
            name="severity_check",
        ),
        CheckConstraint(
            "affected_area_pct IS NULL OR affected_area_pct BETWEEN 0.0 AND 100.0",
            name="area_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drone_scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hole_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    disease_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    affected_area_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_height: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommendation_ko: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    scan: Mapped["DroneScan"] = relationship(
        "DroneScan",
        back_populates="results",
        lazy="selectin",
    )
