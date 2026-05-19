"""add_pin_coordinates_map_path

Revision ID: dead2e65c9f3
Revises: ce81bf52f4a3
Create Date: 2026-05-12 10:30:17.192430

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'dead2e65c9f3'
down_revision: Union[str, Sequence[str], None] = 'ce81bf52f4a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "detection_reports",
        sa.Column(
            "pin_x",
            sa.Float(),
            nullable=True,
            comment="X position as % of map image width 0-100",
        ),
    )
    op.add_column(
        "detection_reports",
        sa.Column(
            "pin_y",
            sa.Float(),
            nullable=True,
            comment="Y position as % of map image height 0-100",
        ),
    )
    op.add_column(
        "golf_courses",
        sa.Column(
            "map_image_path",
            sa.String(length=1024),
            nullable=True,
            comment="Filename of 2D course map image",
        ),
    )
    op.add_column(
        "work_reports",
        sa.Column(
            "mark_type",
            sa.String(length=50),
            nullable=True,
            comment="How worker marked location: pin or polygon",
        ),
    )
    op.add_column(
        "work_reports",
        sa.Column(
            "pin_x",
            sa.Float(),
            nullable=True,
            comment="X position as % of map image width 0-100",
        ),
    )
    op.add_column(
        "work_reports",
        sa.Column(
            "pin_y",
            sa.Float(),
            nullable=True,
            comment="Y position as % of map image height 0-100",
        ),
    )

    for label in ("center", "bottom", "left", "right"):
        with op.get_context().autocommit_block():
            op.execute(
                text(
                    f"""
                    DO $enumadd$ BEGIN
                        ALTER TYPE detection_image_angle ADD VALUE '{label}';
                    EXCEPTION
                        WHEN duplicate_object THEN NULL;
                    END $enumadd$;
                    """
                )
            )

    op.execute(
        text(
            """
            UPDATE detection_images
            SET angle = 'center'::detection_image_angle
            WHERE angle::text = 'north';
            """
        )
    )
    op.execute(
        text(
            """
            UPDATE detection_images
            SET angle = 'bottom'::detection_image_angle
            WHERE angle::text = 'south';
            """
        )
    )
    op.execute(
        text(
            """
            UPDATE detection_images
            SET angle = 'right'::detection_image_angle
            WHERE angle::text = 'east';
            """
        )
    )
    op.execute(
        text(
            """
            UPDATE detection_images
            SET angle = 'left'::detection_image_angle
            WHERE angle::text = 'west';
            """
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("work_reports", "pin_y")
    op.drop_column("work_reports", "pin_x")
    op.drop_column("work_reports", "mark_type")
    op.drop_column("golf_courses", "map_image_path")
    op.drop_column("detection_reports", "pin_y")
    op.drop_column("detection_reports", "pin_x")
