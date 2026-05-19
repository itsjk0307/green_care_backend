"""add_golf_courses_table

Revision ID: b7e4c2f91a5d
Revises: 2dad6b8a5f0a
Create Date: 2026-05-07 16:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql


revision: str = "b7e4c2f91a5d"
down_revision: Union[str, Sequence[str], None] = "2dad6b8a5f0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "golf_courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_ko", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=512), nullable=False),
        sa.Column("address_ko", sa.String(length=512), nullable=False),
        sa.Column("total_area_sqm", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column(
        "reports",
        sa.Column("golf_course_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_reports_golf_course_id_golf_courses",
        "reports",
        "golf_courses",
        ["golf_course_id"],
        ["id"],
    )

    op.execute(
        text(
            """
            INSERT INTO golf_courses (
                id, name, name_ko, address, address_ko, total_area_sqm, is_active
            )
            VALUES
                (
                    gen_random_uuid(),
                    'Yongin Golf Club',
                    '용인 골프클럽',
                    'Yongin, Gyeonggi-do',
                    '경기도 용인시',
                    NULL,
                    true
                ),
                (
                    gen_random_uuid(),
                    'Maysa Green Golf Club',
                    '메이사그린 골프클럽',
                    'Korea',
                    '대한민국',
                    NULL,
                    true
                ),
                (
                    gen_random_uuid(),
                    'Oak Valley Golf Club',
                    '오크밸리 골프클럽',
                    'Wonju, Gangwon-do',
                    '강원도 원주시',
                    NULL,
                    true
                )
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_reports_golf_course_id_golf_courses",
        "reports",
        type_="foreignkey",
    )
    op.drop_column("reports", "golf_course_id")
    op.drop_table("golf_courses")
