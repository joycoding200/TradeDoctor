"""catch_up_missing_migrations

Revision ID: c4tch_up_m1ss1ng
Revises: 8ee879b28b14
Create Date: 2026-06-25 17:10:00.000000

Catch-up migration: several earlier migrations were stamped but never executed.
This applies all the missing schema changes in one migration:

1. raw_files: drop raw_content (LargeBinary), add file_path + file_size
2. Add missing indexes: ix_analyses_raw_file_id, ix_reports_analysis_id, ix_users_phone
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4tch_up_m1ss1ng'
down_revision: Union[str, None] = '8ee879b28b14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. raw_files: drop raw_content, add file_path + file_size
    op.drop_column("raw_files", "raw_content")
    op.add_column("raw_files", sa.Column("file_path", sa.String(1000), nullable=True))
    op.add_column("raw_files", sa.Column("file_size", sa.Integer(), nullable=True))

    # 2. Missing indexes from initial_schema migration
    op.create_index(op.f("ix_analyses_raw_file_id"), "analyses", ["raw_file_id"], unique=False)
    op.create_index(op.f("ix_reports_analysis_id"), "reports", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.drop_index(op.f("ix_reports_analysis_id"), table_name="reports")
    op.drop_index(op.f("ix_analyses_raw_file_id"), table_name="analyses")

    op.drop_column("raw_files", "file_size")
    op.drop_column("raw_files", "file_path")
    op.add_column("raw_files", sa.Column("raw_content", sa.LargeBinary(), nullable=False))
