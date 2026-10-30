"""phase3_learning_and_projects

Revision ID: g67h8i9j0k1l
Revises: f56a7b8c9d0e
Create Date: 2026-10-28 02:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g67h8i9j0k1l'
down_revision: Union[str, Sequence[str], None] = 'f56a7b8c9d0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not inspector.has_table('user_learning_plans'):
        op.create_table(
            'user_learning_plans',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('weekly_hours_budget', sa.Float(), nullable=False, server_default='10.0'),
            sa.Column('target_role', sa.String(255), nullable=True),
            sa.Column('completed_skills', sa.JSON(), nullable=False),
            sa.Column('bookmarked_resources', sa.JSON(), nullable=False),
            sa.Column('project_progress', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_user_learning_plans_id', 'user_learning_plans', ['id'])
        op.create_index('ix_user_learning_plans_user_id', 'user_learning_plans', ['user_id'], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table('user_learning_plans'):
        op.drop_index('ix_user_learning_plans_user_id', table_name='user_learning_plans')
        op.drop_index('ix_user_learning_plans_id', table_name='user_learning_plans')
        op.drop_table('user_learning_plans')
