"""update_drone_scan_constraints

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-05-20 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE drone_scans
        SET image_width = COALESCE(image_width, 0),
            image_height = COALESCE(image_height, 0)
        WHERE image_width IS NULL OR image_height IS NULL
        """
    )
    op.alter_column("drone_scans", "image_width", existing_type=sa.Integer(), nullable=False)
    op.alter_column("drone_scans", "image_height", existing_type=sa.Integer(), nullable=False)

    op.drop_constraint("ck_drone_scans_status", "drone_scans", type_="check")
    op.create_check_constraint(
        "drone_scans_status_check",
        "drone_scans",
        "status IN ('uploaded', 'processing', 'completed', 'failed')",
    )

    op.drop_constraint("ck_scan_results_hole_number", "scan_results", type_="check")
    op.drop_constraint("ck_scan_results_confidence", "scan_results", type_="check")
    op.drop_constraint("ck_scan_results_severity", "scan_results", type_="check")
    op.drop_constraint("ck_scan_results_disease_type", "scan_results", type_="check")

    op.create_check_constraint(
        "hole_number_range",
        "scan_results",
        "hole_number BETWEEN 1 AND 18",
    )
    op.create_check_constraint(
        "confidence_range",
        "scan_results",
        "confidence BETWEEN 0.0 AND 1.0",
    )
    op.create_check_constraint(
        "severity_check",
        "scan_results",
        "severity IS NULL OR severity IN ('low', 'medium', 'high', 'critical')",
    )
    op.create_check_constraint(
        "area_range",
        "scan_results",
        "affected_area_pct IS NULL OR affected_area_pct BETWEEN 0.0 AND 100.0",
    )


def downgrade() -> None:
    op.drop_constraint("area_range", "scan_results", type_="check")
    op.drop_constraint("severity_check", "scan_results", type_="check")
    op.drop_constraint("confidence_range", "scan_results", type_="check")
    op.drop_constraint("hole_number_range", "scan_results", type_="check")

    op.create_check_constraint(
        "ck_scan_results_disease_type",
        "scan_results",
        "disease_type IN ('dollar_spot', 'brown_patch', 'pythium_blight', "
        "'fairy_ring', 'anthracnose', 'leaf_spot', 'healthy')",
    )
    op.create_check_constraint(
        "ck_scan_results_severity",
        "scan_results",
        "severity IS NULL OR severity IN ('low', 'medium', 'high', 'critical')",
    )
    op.create_check_constraint(
        "ck_scan_results_confidence",
        "scan_results",
        "confidence >= 0.0 AND confidence <= 1.0",
    )
    op.create_check_constraint(
        "ck_scan_results_hole_number",
        "scan_results",
        "hole_number >= 1 AND hole_number <= 18",
    )

    op.drop_constraint("drone_scans_status_check", "drone_scans", type_="check")
    op.create_check_constraint(
        "ck_drone_scans_status",
        "drone_scans",
        "status IN ('uploaded', 'processing', 'completed', 'failed')",
    )

    op.alter_column("drone_scans", "image_height", existing_type=sa.Integer(), nullable=True)
    op.alter_column("drone_scans", "image_width", existing_type=sa.Integer(), nullable=True)
