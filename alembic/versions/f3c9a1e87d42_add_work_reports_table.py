"""add_work_reports_table

Revision ID: f3c9a1e87d42
Revises: b7e4c2f91a5d
Create Date: 2026-05-08 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "f3c9a1e87d42"
down_revision: Union[str, Sequence[str], None] = "b7e4c2f91a5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    work_report_status = postgresql.ENUM(
        "in_progress",
        "completed",
        "pending",
        "approved",
        "rejected",
        name="work_report_status",
        create_type=False,
    )
    work_report_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "work_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "work_types",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("before_image_path", sa.String(length=1024), nullable=False),
        sa.Column("after_image_path", sa.String(length=1024), nullable=True),
        sa.Column(
            "zone_coordinates",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("gps_latitude", sa.Float(), nullable=True),
        sa.Column("gps_longitude", sa.Float(), nullable=True),
        sa.Column(
            "gps_route",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            work_report_status,
            nullable=False,
            server_default=sa.text("'in_progress'::work_report_status"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["golf_courses.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("work_reports")
    sa.Enum(name="work_report_status").drop(op.get_bind(), checkfirst=True)
