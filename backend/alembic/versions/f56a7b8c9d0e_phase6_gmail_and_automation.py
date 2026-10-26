"""phase6_gmail_and_automation

Revision ID: f56a7b8c9d0e
Revises: e45f6a7b8c9d
Create Date: 2026-10-19 18:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f56a7b8c9d0e'
down_revision: Union[str, Sequence[str], None] = 'e45f6a7b8c9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. Non-destructively alter outreach_drafts to make opportunity_id nullable with ON DELETE SET NULL
    if inspector.has_table('outreach_drafts'):
        # Check SQLite table info
        col_res = conn.execute(sa.text("PRAGMA table_info(outreach_drafts)"))
        cols_dict = {r[1]: r for r in col_res.fetchall()}
        opp_col = cols_dict.get('opportunity_id')
        
        # Check if opportunity_id is currently NOT NULL (r[3] == 1 in SQLite)
        if opp_col and opp_col[3] == 1:
            conn.execute(sa.text("PRAGMA foreign_keys=OFF;"))
            
            # Recreate outreach_drafts table with nullable opportunity_id and ON DELETE SET NULL
            conn.execute(sa.text("""
                CREATE TABLE outreach_drafts_new (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    opportunity_id VARCHAR(36) REFERENCES opportunities(id) ON DELETE SET NULL,
                    resume_id VARCHAR(36) REFERENCES resumes(id) ON DELETE SET NULL,
                    purpose VARCHAR(50) DEFAULT 'full_time_application' NOT NULL,
                    recipient_type VARCHAR(50) DEFAULT 'hiring_manager' NOT NULL,
                    recipient_name VARCHAR(255),
                    recipient_role VARCHAR(255),
                    subject VARCHAR(500) DEFAULT '' NOT NULL,
                    body TEXT DEFAULT '' NOT NULL,
                    generation_status VARCHAR(50) DEFAULT 'DRAFT' NOT NULL,
                    model_provider VARCHAR(50),
                    model_name VARCHAR(100),
                    context_snapshot JSON DEFAULT '{}' NOT NULL,
                    is_user_edited BOOLEAN DEFAULT 0 NOT NULL,
                    user_notes TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                );
            """))
            conn.execute(sa.text("""
                INSERT INTO outreach_drafts_new (
                    id, user_id, opportunity_id, resume_id, purpose, recipient_type,
                    recipient_name, recipient_role, subject, body, generation_status,
                    model_provider, model_name, context_snapshot, is_user_edited,
                    user_notes, created_at, updated_at
                )
                SELECT
                    id, user_id, opportunity_id, resume_id, purpose, recipient_type,
                    recipient_name, recipient_role, subject, body, generation_status,
                    model_provider, model_name, context_snapshot, is_user_edited,
                    user_notes, created_at, updated_at
                FROM outreach_drafts;
            """))
            conn.execute(sa.text("DROP TABLE outreach_drafts;"))
            conn.execute(sa.text("ALTER TABLE outreach_drafts_new RENAME TO outreach_drafts;"))
            
            # Recreate indexes
            conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_outreach_drafts_user_id ON outreach_drafts(user_id);"))
            conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_outreach_drafts_opportunity_id ON outreach_drafts(opportunity_id);"))
            conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_outreach_drafts_resume_id ON outreach_drafts(resume_id);"))
            conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_outreach_drafts_purpose ON outreach_drafts(purpose);"))
            conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_outreach_drafts_generation_status ON outreach_drafts(generation_status);"))
            
            conn.execute(sa.text("PRAGMA foreign_keys=ON;"))

    # 2. Create gmail_connections table
    if not inspector.has_table('gmail_connections'):
        op.create_table(
            'gmail_connections',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('email_address', sa.String(length=255), nullable=False),
            sa.Column('encrypted_access_token', sa.Text(), nullable=True),
            sa.Column('encrypted_refresh_token', sa.Text(), nullable=False),
            sa.Column('token_expiry', sa.DateTime(timezone=True), nullable=True),
            sa.Column('scopes', sa.JSON(), server_default='[]', nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_gmail_connections_user_id', 'gmail_connections', ['user_id'], unique=True)
        op.create_index('ix_gmail_connections_email_address', 'gmail_connections', ['email_address'])

    # 3. Create outreach_email_messages table
    if not inspector.has_table('outreach_email_messages'):
        op.create_table(
            'outreach_email_messages',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('draft_id', sa.String(length=36), sa.ForeignKey('outreach_drafts.id', ondelete='SET NULL'), nullable=True),
            sa.Column('gmail_connection_id', sa.String(length=36), sa.ForeignKey('gmail_connections.id', ondelete='SET NULL'), nullable=True),
            sa.Column('sender_email', sa.String(length=255), nullable=False),
            sa.Column('recipient_email', sa.String(length=255), nullable=False),
            sa.Column('recipient_name', sa.String(length=255), nullable=True),
            sa.Column('subject', sa.String(length=500), nullable=False),
            sa.Column('body', sa.Text(), nullable=False),
            sa.Column('content_hash', sa.String(length=64), nullable=False),
            sa.Column('idempotency_key', sa.String(length=64), nullable=False),
            sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False),
            sa.Column('gmail_message_id', sa.String(length=128), nullable=True),
            sa.Column('gmail_thread_id', sa.String(length=128), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('has_reply', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('reply_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('last_reply_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_outreach_email_messages_user_id', 'outreach_email_messages', ['user_id'])
        op.create_index('ix_outreach_email_messages_draft_id', 'outreach_email_messages', ['draft_id'])
        op.create_index('ix_outreach_email_messages_recipient_email', 'outreach_email_messages', ['recipient_email'])
        op.create_index('ix_outreach_email_messages_content_hash', 'outreach_email_messages', ['content_hash'])
        op.create_index('ix_outreach_email_messages_idempotency_key', 'outreach_email_messages', ['idempotency_key'], unique=True)
        op.create_index('ix_outreach_email_messages_status', 'outreach_email_messages', ['status'])
        op.create_index('ix_outreach_email_messages_gmail_message_id', 'outreach_email_messages', ['gmail_message_id'])
        op.create_index('ix_outreach_email_messages_gmail_thread_id', 'outreach_email_messages', ['gmail_thread_id'])

    # 4. Create outreach_email_replies table
    if not inspector.has_table('outreach_email_replies'):
        op.create_table(
            'outreach_email_replies',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('message_id', sa.String(length=36), sa.ForeignKey('outreach_email_messages.id', ondelete='CASCADE'), nullable=False),
            sa.Column('gmail_message_id', sa.String(length=128), nullable=False),
            sa.Column('gmail_thread_id', sa.String(length=128), nullable=False),
            sa.Column('from_email', sa.String(length=255), nullable=False),
            sa.Column('from_name', sa.String(length=255), nullable=True),
            sa.Column('subject', sa.String(length=500), nullable=False),
            sa.Column('snippet', sa.Text(), nullable=True),
            sa.Column('body_preview', sa.Text(), nullable=True),
            sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('is_read', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_outreach_email_replies_user_id', 'outreach_email_replies', ['user_id'])
        op.create_index('ix_outreach_email_replies_message_id', 'outreach_email_replies', ['message_id'])
        op.create_index('ix_outreach_email_replies_gmail_message_id', 'outreach_email_replies', ['gmail_message_id'], unique=True)
        op.create_index('ix_outreach_email_replies_gmail_thread_id', 'outreach_email_replies', ['gmail_thread_id'])

    # 5. Create outreach_automation_settings table
    if not inspector.has_table('outreach_automation_settings'):
        op.create_table(
            'outreach_automation_settings',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('sending_mode', sa.String(length=50), server_default='DRAFT_ONLY', nullable=False),
            sa.Column('daily_limit', sa.Integer(), server_default='15', nullable=False),
            sa.Column('emails_sent_today', sa.Integer(), server_default='0', nullable=False),
            sa.Column('last_limit_reset_date', sa.String(length=10), nullable=True),
            sa.Column('cooldown_minutes', sa.Integer(), server_default='15', nullable=False),
            sa.Column('last_sent_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('duplicate_suppression_days', sa.Integer(), server_default='30', nullable=False),
            sa.Column('is_paused', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('auto_followup_enabled', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('followup_delay_days', sa.Integer(), server_default='5', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_outreach_automation_settings_user_id', 'outreach_automation_settings', ['user_id'], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if inspector.has_table('outreach_automation_settings'):
        op.drop_table('outreach_automation_settings')
    if inspector.has_table('outreach_email_replies'):
        op.drop_table('outreach_email_replies')
    if inspector.has_table('outreach_email_messages'):
        op.drop_table('outreach_email_messages')
    if inspector.has_table('gmail_connections'):
        op.drop_table('gmail_connections')
