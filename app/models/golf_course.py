from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GolfCourse(Base):
    __tablename__ = "golf_courses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ko: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(512), nullable=False)
    address_ko: Mapped[str] = mapped_column(String(512), nullable=False)
    total_area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    map_image_path: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Filename of 2D course map image",
    )
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    bound_north: Mapped[float | None] = mapped_column(Float, nullable=True)
    bound_south: Mapped[float | None] = mapped_column(Float, nullable=True)
    bound_east: Mapped[float | None] = mapped_column(Float, nullable=True)
    bound_west: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_zoom: Mapped[int | None] = mapped_column(Integer, nullable=True, default=16)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    work_reports: Mapped[list["WorkReport"]] = relationship(
        "WorkReport",
        back_populates="course",
        foreign_keys="WorkReport.course_id",
    )
    drone_scans: Mapped[list["DroneScan"]] = relationship(
        "DroneScan",
        back_populates="course",
        foreign_keys="DroneScan.course_id",
    )
    work_areas: Mapped[list["WorkArea"]] = relationship(
        "WorkArea",
        back_populates="course",
        foreign_keys="WorkArea.course_id",
    )
    daily_work_plans: Mapped[list["DailyWorkPlan"]] = relationship(
        "DailyWorkPlan",
        back_populates="course",
        foreign_keys="DailyWorkPlan.course_id",
    )
    issues: Mapped[list["Issue"]] = relationship(
        "Issue",
        back_populates="course",
        foreign_keys="Issue.course_id",
    )
