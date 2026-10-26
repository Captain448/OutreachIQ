"""phase5_outreach_drafts

Revision ID: e45f6a7b8c9d
Revises: d34e5f6a7b8c
Create Date: 2026-10-19 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e45f6a7b8c9d'
down_revision: Union[str, Sequence[str], None] = 'd34e5f6a7b8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. Create 'outreach_drafts' table if not exists
    if not inspector.has_table('outreach_drafts'):
        op.create_table(
            'outreach_drafts',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('opportunity_id', sa.String(length=36), sa.ForeignKey('opportunities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('resume_id', sa.String(length=36), sa.ForeignKey('resumes.id', ondelete='SET NULL'), nullable=True),
            sa.Column('purpose', sa.String(length=50), server_default='full_time_application', nullable=False),
            sa.Column('recipient_type', sa.String(length=50), server_default='hiring_manager', nullable=False),
            sa.Column('recipient_name', sa.String(length=255), nullable=True),
            sa.Column('recipient_role', sa.String(length=255), nullable=True),
            sa.Column('subject', sa.String(length=500), server_default='', nullable=False),
            sa.Column('body', sa.Text(), server_default='', nullable=False),
            sa.Column('generation_status', sa.String(length=50), server_default='DRAFT', nullable=False),
            sa.Column('model_provider', sa.String(length=50), nullable=True),
            sa.Column('model_name', sa.String(length=100), nullable=True),
            sa.Column('context_snapshot', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('is_user_edited', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('user_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_outreach_drafts_user_id', 'outreach_drafts', ['user_id'])
        op.create_index('ix_outreach_drafts_opportunity_id', 'outreach_drafts', ['opportunity_id'])
        op.create_index('ix_outreach_drafts_resume_id', 'outreach_drafts', ['resume_id'])
        op.create_index('ix_outreach_drafts_purpose', 'outreach_drafts', ['purpose'])
        op.create_index('ix_outreach_drafts_generation_status', 'outreach_drafts', ['generation_status'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if inspector.has_table('outreach_drafts'):
        op.drop_table('outreach_drafts')
