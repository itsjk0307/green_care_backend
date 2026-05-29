"""update_notifications_table

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-05-20 22:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.alter_column("notifications", "body_ko", existing_type=sa.Text(), nullable=True)
    op.alter_column("notifications", "body_en", existing_type=sa.Text(), nullable=True)

    op.execute(
        """
        ALTER TABLE notifications
        ALTER COLUMN id SET DEFAULT gen_random_uuid()
        """
    )

    op.create_check_constraint(
        "notifications_type_check",
        "notifications",
        "type IN ("
        "'task_assigned', 'issue_flagged', 'issue_resolved', "
        "'issue_assigned', 'ai_result_ready', 'plan_published', "
        "'report_approved', 'report_rejected'"
        ")",
    )
    op.create_check_constraint(
        "notifications_reference_type_check",
        "notifications",
        "reference_type IS NULL OR reference_type IN ("
        "'work_report', 'issue', 'daily_plan', 'drone_scan'"
        ")",
    )

    op.create_index(
        "ix_notifications_user_read_created",
        "notifications",
        ["user_id", "is_read", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index(
        "ix_notifications_user_created",
        "notifications",
        ["user_id", "created_at"],
        postgresql_ops={"created_at": "DESC"},
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_index("ix_notifications_user_read_created", table_name="notifications")
    op.drop_constraint("notifications_reference_type_check", "notifications", type_="check")
    op.drop_constraint("notifications_type_check", "notifications", type_="check")
    op.alter_column("notifications", "body_en", existing_type=sa.Text(), nullable=False)
    op.alter_column("notifications", "body_ko", existing_type=sa.Text(), nullable=False)
