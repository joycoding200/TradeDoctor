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
    # 1. raw_files: drop raw_content (if exists), add file_path + file_size (if not exists)
    #    Production databases may already have these columns — make operations conditional.
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    raw_files_cols = {c["name"] for c in inspector.get_columns("raw_files")}

    if "raw_content" in raw_files_cols:
        op.drop_column("raw_files", "raw_content")
    if "file_path" not in raw_files_cols:
        op.add_column("raw_files", sa.Column("file_path", sa.String(1000), nullable=True))
    if "file_size" not in raw_files_cols:
        op.add_column("raw_files", sa.Column("file_size", sa.Integer(), nullable=True))

    # 2. Missing indexes — only create if not already present
    existing_indexes = {i["name"] for i in inspector.get_indexes("analyses")}
    if "ix_analyses_raw_file_id" not in existing_indexes:
        op.create_index(op.f("ix_analyses_raw_file_id"), "analyses", ["raw_file_id"], unique=False)

    existing_indexes = {i["name"] for i in inspector.get_indexes("reports")}
    if "ix_reports_analysis_id" not in existing_indexes:
        op.create_index(op.f("ix_reports_analysis_id"), "reports", ["analysis_id"], unique=False)

    existing_indexes = {i["name"] for i in inspector.get_indexes("users")}
    if "ix_users_phone" not in existing_indexes:
        op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Drop indexes (only if they exist)
    existing_indexes = {i["name"] for i in inspector.get_indexes("users")}
    if "ix_users_phone" in existing_indexes:
        op.drop_index(op.f("ix_users_phone"), table_name="users")

    existing_indexes = {i["name"] for i in inspector.get_indexes("reports")}
    if "ix_reports_analysis_id" in existing_indexes:
        op.drop_index(op.f("ix_reports_analysis_id"), table_name="reports")

    existing_indexes = {i["name"] for i in inspector.get_indexes("analyses")}
    if "ix_analyses_raw_file_id" in existing_indexes:
        op.drop_index(op.f("ix_analyses_raw_file_id"), table_name="analyses")

    # Reverse file_path/file_size changes
    raw_files_cols = {c["name"] for c in inspector.get_columns("raw_files")}
    if "file_size" in raw_files_cols:
        op.drop_column("raw_files", "file_size")
    if "file_path" in raw_files_cols:
        op.drop_column("raw_files", "file_path")
    if "raw_content" not in raw_files_cols:
        op.add_column("raw_files", sa.Column("raw_content", sa.LargeBinary(), nullable=False))
