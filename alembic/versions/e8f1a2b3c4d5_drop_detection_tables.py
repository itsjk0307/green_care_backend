"""drop_old_detection_tables

Revision ID: e8f1a2b3c4d5
Revises: dcefeef6c7b2
Create Date: 2026-05-20 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "e8f1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "dcefeef6c7b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("detection_images")
    op.drop_table("detection_reports")


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade not supported: detection tables were replaced by drone_scans."
    )
