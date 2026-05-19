from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DailyWorkPlan(Base):
    __tablename__ = "daily_work_plans"
    __table_args__ = (
        UniqueConstraint("course_id", "plan_date", name="uq_daily_work_plans_course_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("golf_courses.id"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    plan_date: Mapped[date] = mapped_column(Date, nullable=False)
    weather: Mapped[str] = mapped_column(String(50), nullable=False)
    temperature_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    special_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_workers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    course: Mapped["GolfCourse"] = relationship(
        "GolfCourse",
        foreign_keys=[course_id],
        back_populates="daily_work_plans",
    )
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_daily_work_plans",
    )
    zone_tasks: Mapped[list["DailyZoneTask"]] = relationship(
        "DailyZoneTask",
        back_populates="plan",
        cascade="all, delete-orphan",
    )
    attendance: Mapped[list["DailyWorkerAttendance"]] = relationship(
        "DailyWorkerAttendance",
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class DailyZoneTask(Base):
    __tablename__ = "daily_zone_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("daily_work_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    zone: Mapped[str] = mapped_column(String(50), nullable=False)
    task_types: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    mowing_height_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    assigned_worker_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    plan: Mapped["DailyWorkPlan"] = relationship(
        "DailyWorkPlan",
        back_populates="zone_tasks",
    )


class DailyWorkerAttendance(Base):
    __tablename__ = "daily_worker_attendance"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("daily_work_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="present")
    start_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    end_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    working_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    plan: Mapped["DailyWorkPlan"] = relationship(
        "DailyWorkPlan",
        back_populates="attendance",
    )
    worker: Mapped["User"] = relationship(
        "User",
        foreign_keys=[worker_id],
        back_populates="daily_attendance_records",
    )
