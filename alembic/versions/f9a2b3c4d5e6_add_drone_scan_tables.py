"""create_drone_scan_tables

Revision ID: f9a2b3c4d5e6
Revises: e8f1a2b3c4d5
Create Date: 2026-05-20 14:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f9a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e8f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "drone_scans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_date", sa.Date(), nullable=False),
        sa.Column("image_path", sa.String(length=1024), nullable=False),
        sa.Column("image_width", sa.Integer(), nullable=True),
        sa.Column("image_height", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('uploaded', 'processing', 'completed', 'failed')",
            name="ck_drone_scans_status",
        ),
        sa.ForeignKeyConstraint(["course_id"], ["golf_courses.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drone_scans_course_id", "drone_scans", ["course_id"])
    op.create_index("ix_drone_scans_status", "drone_scans", ["status"])
    op.create_index("ix_drone_scans_created_at", "drone_scans", ["created_at"])

    op.create_table(
        "scan_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hole_number", sa.Integer(), nullable=False),
        sa.Column("disease_type", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column("affected_area_pct", sa.Float(), nullable=True),
        sa.Column("bbox_x", sa.Float(), nullable=True),
        sa.Column("bbox_y", sa.Float(), nullable=True),
        sa.Column("bbox_width", sa.Float(), nullable=True),
        sa.Column("bbox_height", sa.Float(), nullable=True),
        sa.Column("recommendation_ko", sa.Text(), nullable=True),
        sa.Column("recommendation_en", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "hole_number >= 1 AND hole_number <= 18",
            name="ck_scan_results_hole_number",
        ),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_scan_results_confidence",
        ),
        sa.CheckConstraint(
            "severity IS NULL OR severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_scan_results_severity",
        ),
        sa.CheckConstraint(
            "disease_type IN ("
            "'dollar_spot', 'brown_patch', 'pythium_blight', "
            "'fairy_ring', 'anthracnose', 'leaf_spot', 'healthy'"
            ")",
            name="ck_scan_results_disease_type",
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["drone_scans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_results_scan_id", "scan_results", ["scan_id"])
    op.create_index("ix_scan_results_hole_number", "scan_results", ["hole_number"])


def downgrade() -> None:
    op.drop_index("ix_scan_results_hole_number", table_name="scan_results")
    op.drop_index("ix_scan_results_scan_id", table_name="scan_results")
    op.drop_table("scan_results")
    op.drop_index("ix_drone_scans_created_at", table_name="drone_scans")
    op.drop_index("ix_drone_scans_status", table_name="drone_scans")
    op.drop_index("ix_drone_scans_course_id", table_name="drone_scans")
    op.drop_table("drone_scans")
