"""add_analysis_snapshots

Revision ID: 8a1b2c3d4e5f
Revises: bc2993dcbbae
Create Date: 2026-06-26 12:00:00.000000

Add insight_snapshot, whatif_snapshot, and computed_at columns to analyses table
for write-time computation / read-time cache strategy.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8a1b2c3d4e5f'
down_revision: Union[str, None] = 'bc2993dcbbae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('analyses', sa.Column('insight_snapshot', postgresql.JSONB, nullable=True))
    op.add_column('analyses', sa.Column('whatif_snapshot', postgresql.JSONB, nullable=True))
    op.add_column('analyses', sa.Column('computed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('analyses', 'computed_at')
    op.drop_column('analyses', 'whatif_snapshot')
    op.drop_column('analyses', 'insight_snapshot')
