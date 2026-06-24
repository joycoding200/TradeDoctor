"""raw_content to file_path + file_size

Revision ID: manual_raw
Revises: 662118d57511
Create Date: 2026-06-24

Drops the LargeBinary raw_content column (files now live on disk under
backend/uploads/) and adds file_path + file_size metadata columns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "manual_raw"
down_revision: Union[str, None] = "662118d57511"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("raw_files", "raw_content")
    op.add_column("raw_files", sa.Column("file_path", sa.String(1000), nullable=True))
    op.add_column("raw_files", sa.Column("file_size", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("raw_files", "file_size")
    op.drop_column("raw_files", "file_path")
    op.add_column("raw_files", sa.Column("raw_content", sa.LargeBinary(), nullable=False))
