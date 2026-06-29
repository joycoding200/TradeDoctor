"""add_symbol_name_to_trades

Revision ID: b2c3d4e5f6a7
Revises: d7e2f1a3b456
Create Date: 2026-06-29 12:00:00.000000

Add nullable symbol_name column to trades so the SymbolSummaryTable can
show the Chinese security name (e.g. "北方华创") next to the code.
Existing rows are left as NULL; new imports populate the column when the
broker file includes a 证券名称 / 股票名称 column.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "d7e2f1a3b456"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column only if it does not already exist (idempotent for re-runs).
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("trades")}
    if "symbol_name" not in cols:
        op.add_column(
            "trades",
            sa.Column("symbol_name", sa.String(length=50), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("trades")}
    if "symbol_name" in cols:
        op.drop_column("trades", "symbol_name")
