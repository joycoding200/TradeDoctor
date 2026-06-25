"""make_email_nullable

Revision ID: 8ee879b28b14
Revises: 4b5cc5fa0342
Create Date: 2026-06-25 16:57:00.000000

Fix: users.email was NOT NULL in DB but nullable in SQLAlchemy model.
Phone-only registration failed because it sends email=NULL.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8ee879b28b14'
down_revision: Union[str, None] = '4b5cc5fa0342'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'email',
                    existing_type=sa.VARCHAR(length=255),
                    nullable=True)


def downgrade() -> None:
    op.alter_column('users', 'email',
                    existing_type=sa.VARCHAR(length=255),
                    nullable=False)
