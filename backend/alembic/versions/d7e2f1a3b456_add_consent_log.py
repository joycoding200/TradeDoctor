"""add_consent_log

Revision ID: d7e2f1a3b456
Revises: 8a1b2c3d4e5f
Create Date: 2026-06-26 10:00:00.000000

Add consent_log table for audit trail of case library consent decisions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7e2f1a3b456'
down_revision: Union[str, None] = '8a1b2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'consent_log',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('analysis_id', sa.String(36), nullable=True),
        sa.Column('consented', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['analysis_id'], ['analyses.id'],
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_consent_log_user_id'), 'consent_log', ['user_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_consent_log_user_id'), table_name='consent_log')
    op.drop_table('consent_log')
