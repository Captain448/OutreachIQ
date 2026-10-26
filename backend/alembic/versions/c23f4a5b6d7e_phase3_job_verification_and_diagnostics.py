"""phase3_job_verification_and_diagnostics

Revision ID: c23f4a5b6d7e
Revises: b12e3f4a5c6d
Create Date: 2026-10-18 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c23f4a5b6d7e'
down_revision: Union[str, Sequence[str], None] = 'b12e3f4a5c6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. Inspect existing columns and indexes for 'jobs'
    existing_job_cols = {c['name'] for c in inspector.get_columns('jobs')} if inspector.has_table('jobs') else set()
    existing_job_indexes = {ix['name'] for ix in inspector.get_indexes('jobs')} if inspector.has_table('jobs') else set()

    with op.batch_alter_table('jobs', schema=None) as batch_op:
        if 'application_url' not in existing_job_cols:
            batch_op.add_column(sa.Column('application_url', sa.String(length=1000), nullable=True))
        if 'salary_range' not in existing_job_cols:
            batch_op.add_column(sa.Column('salary_range', sa.String(length=100), nullable=True))
        if 'verification_status' not in existing_job_cols:
            batch_op.add_column(sa.Column('verification_status', sa.String(length=50), server_default='LISTING_FOUND_STATUS_UNVERIFIED', nullable=False))
        if 'verification_details' not in existing_job_cols:
            batch_op.add_column(sa.Column('verification_details', sa.JSON(), server_default='{}', nullable=False))
        if 'is_verified' not in existing_job_cols:
            batch_op.add_column(sa.Column('is_verified', sa.Boolean(), server_default='0', nullable=False))
        if 'last_verified_at' not in existing_job_cols:
            batch_op.add_column(sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True))
        if 'ix_jobs_verification_status' not in existing_job_indexes:
            batch_op.create_index(batch_op.f('ix_jobs_verification_status'), ['verification_status'], unique=False)

    # 2. Inspect 'agent_runs'
    existing_run_cols = {c['name'] for c in inspector.get_columns('agent_runs')} if inspector.has_table('agent_runs') else set()
    with op.batch_alter_table('agent_runs', schema=None) as batch_op:
        if 'diagnostics' not in existing_run_cols:
            batch_op.add_column(sa.Column('diagnostics', sa.JSON(), server_default='{}', nullable=False))

    # 3. Inspect 'opportunities'
    existing_opp_cols = {c['name'] for c in inspector.get_columns('opportunities')} if inspector.has_table('opportunities') else set()
    with op.batch_alter_table('opportunities', schema=None) as batch_op:
        if 'extraction_quality' not in existing_opp_cols:
            batch_op.add_column(sa.Column('extraction_quality', sa.Float(), server_default='1.0', nullable=False))
        if 'company_confidence' not in existing_opp_cols:
            batch_op.add_column(sa.Column('company_confidence', sa.Float(), server_default='1.0', nullable=False))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing_opp_cols = {c['name'] for c in inspector.get_columns('opportunities')} if inspector.has_table('opportunities') else set()
    with op.batch_alter_table('opportunities', schema=None) as batch_op:
        if 'company_confidence' in existing_opp_cols:
            batch_op.drop_column('company_confidence')
        if 'extraction_quality' in existing_opp_cols:
            batch_op.drop_column('extraction_quality')

    existing_run_cols = {c['name'] for c in inspector.get_columns('agent_runs')} if inspector.has_table('agent_runs') else set()
    with op.batch_alter_table('agent_runs', schema=None) as batch_op:
        if 'diagnostics' in existing_run_cols:
            batch_op.drop_column('diagnostics')

    existing_job_cols = {c['name'] for c in inspector.get_columns('jobs')} if inspector.has_table('jobs') else set()
    existing_job_indexes = {ix['name'] for ix in inspector.get_indexes('jobs')} if inspector.has_table('jobs') else set()
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        if 'ix_jobs_verification_status' in existing_job_indexes:
            batch_op.drop_index(batch_op.f('ix_jobs_verification_status'))
        if 'last_verified_at' in existing_job_cols:
            batch_op.drop_column('last_verified_at')
        if 'is_verified' in existing_job_cols:
            batch_op.drop_column('is_verified')
        if 'verification_details' in existing_job_cols:
            batch_op.drop_column('verification_details')
        if 'verification_status' in existing_job_cols:
            batch_op.drop_column('verification_status')
        if 'salary_range' in existing_job_cols:
            batch_op.drop_column('salary_range')
        if 'application_url' in existing_job_cols:
            batch_op.drop_column('application_url')
