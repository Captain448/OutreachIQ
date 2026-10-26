"""phase4_cosgo_skill_gap_optimization

Revision ID: d34e5f6a7b8c
Revises: c23f4a5b6d7e
Create Date: 2026-10-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd34e5f6a7b8c'
down_revision: Union[str, Sequence[str], None] = 'c23f4a5b6d7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. Create 'cosgo_runs' if not present
    if not inspector.has_table('cosgo_runs'):
        op.create_table(
            'cosgo_runs',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('budget_hours', sa.Float(), server_default='40.0', nullable=False),
            sa.Column('weekly_budget_hours', sa.Float(), server_default='10.0', nullable=False),
            sa.Column('target_roles', sa.JSON(), server_default='[]', nullable=False),
            sa.Column('algorithm_version', sa.String(length=50), server_default='cosgo-v1.0', nullable=False),
            sa.Column('status', sa.String(length=50), server_default='completed', nullable=False),
            sa.Column('total_opportunities_analyzed', sa.Integer(), server_default='0', nullable=False),
            sa.Column('eligible_opportunities_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('excluded_opportunities_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('baseline_coverage', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('projected_coverage', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('marginal_coverage_increase', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('opportunities_at_threshold_baseline', sa.Integer(), server_default='0', nullable=False),
            sa.Column('opportunities_at_threshold_projected', sa.Integer(), server_default='0', nullable=False),
            sa.Column('diagnostics', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('opportunity_weights_used', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_cosgo_runs_id', 'cosgo_runs', ['id'])
        op.create_index('ix_cosgo_runs_user_id', 'cosgo_runs', ['user_id'])

    # 2. Create 'cosgo_actions' if not present
    if not inspector.has_table('cosgo_actions'):
        op.create_table(
            'cosgo_actions',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('run_id', sa.String(length=36), sa.ForeignKey('cosgo_runs.id', ondelete='CASCADE'), nullable=False),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('skill_name', sa.String(length=100), nullable=False),
            sa.Column('category', sa.String(length=50), server_default='technical', nullable=False),
            sa.Column('priority_rank', sa.Integer(), nullable=False),
            sa.Column('estimated_hours', sa.Float(), nullable=False),
            sa.Column('effort_uncertainty_range', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('marginal_coverage_gain', sa.Float(), nullable=False),
            sa.Column('cumulative_coverage', sa.Float(), nullable=False),
            sa.Column('opportunities_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('target_opportunity_ids', sa.JSON(), server_default='[]', nullable=False),
            sa.Column('target_opportunities_summary', sa.JSON(), server_default='[]', nullable=False),
            sa.Column('prerequisites', sa.JSON(), server_default='[]', nullable=False),
            sa.Column('why_recommended', sa.Text(), nullable=True),
            sa.Column('practical_project', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('learning_resources', sa.JSON(), server_default='[]', nullable=False),
            sa.Column('progress_state', sa.String(length=50), server_default='RECOMMENDED', nullable=False),
            sa.Column('user_notes', sa.Text(), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_cosgo_actions_id', 'cosgo_actions', ['id'])
        op.create_index('ix_cosgo_actions_run_id', 'cosgo_actions', ['run_id'])
        op.create_index('ix_cosgo_actions_user_id', 'cosgo_actions', ['user_id'])
        op.create_index('ix_cosgo_actions_skill_name', 'cosgo_actions', ['skill_name'])
        op.create_index('ix_cosgo_actions_progress_state', 'cosgo_actions', ['progress_state'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table('cosgo_actions'):
        op.drop_table('cosgo_actions')
    if inspector.has_table('cosgo_runs'):
        op.drop_table('cosgo_runs')
