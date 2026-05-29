from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
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


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (
        CheckConstraint(
            "issue_type IN ('disease', 'equipment', 'irrigation', 'turf_damage', 'other')",
            name="issues_issue_type_check",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="issues_priority_check",
        ),
        CheckConstraint(
            "pin_x BETWEEN 0.0 AND 100.0",
            name="issues_pin_x_check",
        ),
        CheckConstraint(
            "pin_y BETWEEN 0.0 AND 100.0",
            name="issues_pin_y_check",
        ),
        CheckConstraint(
            "hole_number IS NULL OR hole_number BETWEEN 1 AND 18",
            name="issues_hole_number_check",
        ),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved')",
            name="issues_status_check",
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
    reported_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="medium",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pin_x: Mapped[float] = mapped_column(Float, nullable=False)
    pin_y: Mapped[float] = mapped_column(Float, nullable=False)
    hole_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="open",
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    course: Mapped["GolfCourse"] = relationship(
        "GolfCourse",
        back_populates="issues",
        foreign_keys=[course_id],
    )
    reporter: Mapped["User"] = relationship(
        "User",
        back_populates="reported_issues",
        foreign_keys=[reported_by],
    )
    assignee: Mapped["User | None"] = relationship(
        "User",
        back_populates="assigned_issues",
        foreign_keys=[assigned_to],
    )
