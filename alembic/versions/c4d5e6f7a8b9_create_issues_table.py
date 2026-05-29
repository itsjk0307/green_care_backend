"""create_issues_table

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-05-20 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "issues",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reported_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("issue_type", sa.String(length=64), nullable=False),
        sa.Column(
            "priority",
            sa.String(length=32),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_path", sa.String(length=1024), nullable=True),
        sa.Column("pin_x", sa.Float(), nullable=False),
        sa.Column("pin_y", sa.Float(), nullable=False),
        sa.Column("hole_number", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="open",
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "issue_type IN ('disease', 'equipment', 'irrigation', 'turf_damage', 'other')",
            name="issues_issue_type_check",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="issues_priority_check",
        ),
        sa.CheckConstraint(
            "pin_x BETWEEN 0.0 AND 100.0",
            name="issues_pin_x_check",
        ),
        sa.CheckConstraint(
            "pin_y BETWEEN 0.0 AND 100.0",
            name="issues_pin_y_check",
        ),
        sa.CheckConstraint(
            "hole_number IS NULL OR hole_number BETWEEN 1 AND 18",
            name="issues_hole_number_check",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved')",
            name="issues_status_check",
        ),
        sa.ForeignKeyConstraint(["course_id"], ["golf_courses.id"]),
        sa.ForeignKeyConstraint(["reported_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_issues_course_status_priority",
        "issues",
        ["course_id", "status", "priority"],
    )
    op.create_index("ix_issues_assigned_to", "issues", ["assigned_to"])


def downgrade() -> None:
    op.drop_index("ix_issues_assigned_to", table_name="issues")
    op.drop_index("ix_issues_course_status_priority", table_name="issues")
    op.drop_table("issues")
