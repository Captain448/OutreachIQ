"""add_company_classification

Revision ID: b12e3f4a5c6d
Revises: 760d4bada1cc
Create Date: 2026-10-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b12e3f4a5c6d'
down_revision: Union[str, Sequence[str], None] = '760d4bada1cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.add_column(sa.Column('classification', sa.String(length=50), server_default='unknown', nullable=False))
        batch_op.create_index(batch_op.f('ix_companies_classification'), ['classification'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_companies_classification'))
        batch_op.drop_column('classification')
