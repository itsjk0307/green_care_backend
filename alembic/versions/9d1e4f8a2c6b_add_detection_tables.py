"""add_detection_tables

Revision ID: 9d1e4f8a2c6b
Revises: f3c9a1e87d42
Create Date: 2026-05-08 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "9d1e4f8a2c6b"
down_revision: Union[str, Sequence[str], None] = "f3c9a1e87d42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    detection_upload_source = postgresql.ENUM(
        "mobile", "web", "drone", name="detection_upload_source", create_type=False
    )
    detection_condition = postgresql.ENUM(
        "good",
        "disease_found",
        "processing",
        name="detection_condition",
        create_type=False,
    )
    detection_report_status = postgresql.ENUM(
        "processing",
        "completed",
        "approved",
        "flagged",
        name="detection_report_status",
        create_type=False,
    )
    detection_image_angle = postgresql.ENUM(
        "top",
        "north",
        "south",
        "east",
        "west",
        "close_up",
        name="detection_image_angle",
        create_type=False,
    )

    detection_upload_source.create(op.get_bind(), checkfirst=True)
    detection_condition.create(op.get_bind(), checkfirst=True)
    detection_report_status.create(op.get_bind(), checkfirst=True)
    detection_image_angle.create(op.get_bind(), checkfirst=True)

    severity_level = postgresql.ENUM(
        "low",
        "moderate",
        "high",
        "critical",
        name="severity_level",
        create_type=False,
    )

    op.create_table(
        "detection_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "zone_coordinates",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("gps_latitude", sa.Float(), nullable=True),
        sa.Column("gps_longitude", sa.Float(), nullable=True),
        sa.Column(
            "upload_source",
            detection_upload_source,
            nullable=False,
            server_default=sa.text("'mobile'::detection_upload_source"),
        ),
        sa.Column("drone_height_m", sa.Float(), nullable=True),
        sa.Column(
            "condition",
            detection_condition,
            nullable=False,
            server_default=sa.text("'processing'::detection_condition"),
        ),
        sa.Column("disease_type", sa.String(length=255), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("severity", severity_level, nullable=True),
        sa.Column("affected_area_percent", sa.Float(), nullable=True),
        sa.Column("recommendation_en", sa.Text(), nullable=True),
        sa.Column("recommendation_ko", sa.Text(), nullable=True),
        sa.Column(
            "ai_model_version",
            sa.String(length=50),
            nullable=False,
            server_default="mock-1.0.0",
        ),
        sa.Column(
            "status",
            detection_report_status,
            nullable=False,
            server_default=sa.text("'processing'::detection_report_status"),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["golf_courses.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "detection_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("detection_report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_path", sa.String(length=1024), nullable=False),
        sa.Column("angle", detection_image_angle, nullable=True),
        sa.Column("file_size_mb", sa.Float(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["detection_report_id"],
            ["detection_reports.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("detection_images")
    op.drop_table("detection_reports")

    sa.Enum(name="detection_image_angle").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="detection_report_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="detection_condition").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="detection_upload_source").drop(op.get_bind(), checkfirst=True)
