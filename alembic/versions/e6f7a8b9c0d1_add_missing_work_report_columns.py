"""add_missing_work_report_columns

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-05-28 10:00:00.000000

Adds gps_latitude, gps_longitude, mark_type, pin_x, pin_y to work_reports
using IF NOT EXISTS so the migration is safe even if some columns already
exist (e.g. created by an earlier migration applied on a different DB).
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE work_reports
            ADD COLUMN IF NOT EXISTS gps_latitude   DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS gps_longitude  DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS mark_type      VARCHAR(50),
            ADD COLUMN IF NOT EXISTS pin_x          DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS pin_y          DOUBLE PRECISION
        """
    )


def downgrade() -> None:
    # These columns may have existed before this migration; skip dropping them
    # to avoid destroying data that existed in an earlier schema version.
    pass
