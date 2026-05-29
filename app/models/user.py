from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    worker = "worker"
    admin = "admin"
    manager = "manager"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.worker,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    reports: Mapped[list["Report"]] = relationship(
        "Report",
        back_populates="user",
        foreign_keys="Report.user_id",
    )
    authored_work_reports: Mapped[list["WorkReport"]] = relationship(
        "WorkReport",
        back_populates="worker",
        foreign_keys="WorkReport.worker_id",
    )
    reviewed_work_reports: Mapped[list["WorkReport"]] = relationship(
        "WorkReport",
        back_populates="reviewer",
        foreign_keys="WorkReport.approved_by",
    )
    uploaded_drone_scans: Mapped[list["DroneScan"]] = relationship(
        "DroneScan",
        back_populates="uploader",
        foreign_keys="DroneScan.uploaded_by",
    )
    created_daily_work_plans: Mapped[list["DailyWorkPlan"]] = relationship(
        "DailyWorkPlan",
        back_populates="creator",
        foreign_keys="DailyWorkPlan.created_by",
    )
    daily_attendance_records: Mapped[list["DailyWorkerAttendance"]] = relationship(
        "DailyWorkerAttendance",
        back_populates="worker",
        foreign_keys="DailyWorkerAttendance.worker_id",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        foreign_keys="Notification.user_id",
    )
    reported_issues: Mapped[list["Issue"]] = relationship(
        "Issue",
        back_populates="reporter",
        foreign_keys="Issue.reported_by",
    )
    assigned_issues: Mapped[list["Issue"]] = relationship(
        "Issue",
        back_populates="assignee",
        foreign_keys="Issue.assigned_to",
    )

