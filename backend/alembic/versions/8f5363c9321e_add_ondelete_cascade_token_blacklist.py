"""add_ondelete_cascade_token_blacklist

Revision ID: 8f5363c9321e
Revises: manual_raw
Create Date: 2026-06-25 12:15:06.000569

Changes:
  - Add ON DELETE CASCADE / SET NULL to all foreign keys
  - Make reports.validation_passed NOT NULL
  - Create token_blacklist table for JWT revocation (logout)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '8f5363c9321e'
down_revision: Union[str, None] = 'manual_raw'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _safe_rebuild_fk(table_name: str, constraint_name: str, ref_table: str,
                     columns: list[str], ondelete: str | None) -> None:
    """Drop and recreate a foreign key constraint if it exists.

    Constraint names and table names in this migration are all hardcoded
    literals (not user input), so string formatting is safe here.
    """
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            f"SELECT 1 FROM pg_constraint "
            f"WHERE conname = '{constraint_name}' AND conrelid = '{table_name}'::regclass"
        )
    ).fetchone()

    if result:
        op.drop_constraint(constraint_name, table_name, type_="foreignkey")

    op.create_foreign_key(
        constraint_name, table_name, ref_table, columns, ["id"],
        ondelete=ondelete,
    )


def upgrade() -> None:
    # 0. Clean orphaned references before creating FKs
    op.execute(sa.text(
        "UPDATE reports SET analysis_id = NULL "
        "WHERE analysis_id IS NOT NULL "
        "AND analysis_id NOT IN (SELECT id FROM analyses)"
    ))

    # 1. Rebuild FKs with ondelete
    fk_changes = [
        ("raw_files",    "raw_files_user_id_fkey",     "users",     ["user_id"],     "CASCADE"),
        ("trades",       "trades_raw_file_id_fkey",    "raw_files", ["raw_file_id"], "CASCADE"),
        ("trades",       "trades_user_id_fkey",        "users",     ["user_id"],     "CASCADE"),
        ("analyses",     "analyses_user_id_fkey",      "users",     ["user_id"],     "CASCADE"),
        ("analyses",     "analyses_raw_file_id_fkey",  "raw_files", ["raw_file_id"], "SET NULL"),
        ("reports",      "reports_user_id_fkey",       "users",     ["user_id"],     "CASCADE"),
        ("reports",      "reports_analysis_id_fkey",   "analyses",  ["analysis_id"], "SET NULL"),
        ("positions",    "positions_user_id_fkey",     "users",     ["user_id"],     "CASCADE"),
        ("patterns",     "patterns_position_id_fkey",  "positions", ["position_id"], "CASCADE"),
        ("case_library", "case_library_user_id_fkey",  "users",     ["user_id"],     "CASCADE"),
        ("case_library", "case_library_analysis_id_fkey", "analyses", ["analysis_id"], "CASCADE"),
    ]
    for table, cname, ref, cols, ondel in fk_changes:
        _safe_rebuild_fk(table, cname, ref, cols, ondel)

    # 2. reports.validation_passed → NOT NULL
    op.execute(sa.text("UPDATE reports SET validation_passed = TRUE WHERE validation_passed IS NULL"))
    with op.batch_alter_table("reports") as batch:
        batch.alter_column("validation_passed", nullable=False, server_default=sa.true())

    # 3. Create token_blacklist table
    op.create_table(
        "token_blacklist",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("jti", sa.String(36), nullable=False, unique=True, index=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    # 1. Drop token_blacklist table
    op.drop_table("token_blacklist")

    # 2. Revert validation_passed to nullable
    with op.batch_alter_table("reports") as batch:
        batch.alter_column("validation_passed", nullable=True, server_default=None)

    # 3. Rebuild FKs without ondelete
    fk_changes = [
        ("raw_files",    "raw_files_user_id_fkey",     "users",     ["user_id"]),
        ("trades",       "trades_raw_file_id_fkey",    "raw_files", ["raw_file_id"]),
        ("trades",       "trades_user_id_fkey",        "users",     ["user_id"]),
        ("analyses",     "analyses_user_id_fkey",      "users",     ["user_id"]),
        ("analyses",     "analyses_raw_file_id_fkey",  "raw_files", ["raw_file_id"]),
        ("reports",      "reports_user_id_fkey",       "users",     ["user_id"]),
        ("reports",      "reports_analysis_id_fkey",   "analyses",  ["analysis_id"]),
        ("positions",    "positions_user_id_fkey",     "users",     ["user_id"]),
        ("patterns",     "patterns_position_id_fkey",  "positions", ["position_id"]),
        ("case_library", "case_library_user_id_fkey",  "users",     ["user_id"]),
        ("case_library", "case_library_analysis_id_fkey", "analyses", ["analysis_id"]),
    ]
    for table, cname, ref, cols in fk_changes:
        _safe_rebuild_fk(table, cname, ref, cols, None)
