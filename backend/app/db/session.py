from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator

from app.core.config import settings

connect_args = {}
if "sqlite" in settings.sync_database_url:
    connect_args = {
        "check_same_thread": False,
        "timeout": 30.0
    }

engine = create_engine(
    settings.sync_database_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

if "sqlite" in settings.sync_database_url and ":memory:" not in settings.sync_database_url:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")  # 30 seconds
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_schema_compatibility():
    """Safely adds missing columns without altering or resetting existing tables."""
    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            # 1. Check companies table
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'"))
            if res.fetchone():
                col_res = conn.execute(text("PRAGMA table_info(companies)"))
                cols = [r[1] for r in col_res.fetchall()]
                if "classification" not in cols:
                    conn.execute(text("ALTER TABLE companies ADD COLUMN classification VARCHAR(50) DEFAULT 'unknown' NOT NULL"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_companies_classification ON companies(classification)"))

            # 2. Check jobs table
            res_jobs = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"))
            if res_jobs.fetchone():
                col_res = conn.execute(text("PRAGMA table_info(jobs)"))
                cols = [r[1] for r in col_res.fetchall()]
                if "application_url" not in cols:
                    conn.execute(text("ALTER TABLE jobs ADD COLUMN application_url VARCHAR(1000)"))
                if "salary_range" not in cols:
                    conn.execute(text("ALTER TABLE jobs ADD COLUMN salary_range VARCHAR(100)"))
                if "verification_status" not in cols:
                    conn.execute(text("ALTER TABLE jobs ADD COLUMN verification_status VARCHAR(50) DEFAULT 'LISTING_FOUND_STATUS_UNVERIFIED' NOT NULL"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_verification_status ON jobs(verification_status)"))
                if "verification_details" not in cols:
                    conn.execute(text("ALTER TABLE jobs ADD COLUMN verification_details JSON DEFAULT '{}' NOT NULL"))
                if "is_verified" not in cols:
                    conn.execute(text("ALTER TABLE jobs ADD COLUMN is_verified BOOLEAN DEFAULT 0 NOT NULL"))
                if "last_verified_at" not in cols:
                    conn.execute(text("ALTER TABLE jobs ADD COLUMN last_verified_at TIMESTAMP"))

            # 3. Check agent_runs table
            res_runs = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_runs'"))
            if res_runs.fetchone():
                col_res = conn.execute(text("PRAGMA table_info(agent_runs)"))
                cols = [r[1] for r in col_res.fetchall()]
                if "diagnostics" not in cols:
                    conn.execute(text("ALTER TABLE agent_runs ADD COLUMN diagnostics JSON DEFAULT '{}' NOT NULL"))

            # 4. Check opportunities table
            res_opps = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='opportunities'"))
            if res_opps.fetchone():
                col_res = conn.execute(text("PRAGMA table_info(opportunities)"))
                cols = [r[1] for r in col_res.fetchall()]
                if "extraction_quality" not in cols:
                    conn.execute(text("ALTER TABLE opportunities ADD COLUMN extraction_quality FLOAT DEFAULT 1.0 NOT NULL"))
                if "company_confidence" not in cols:
                    conn.execute(text("ALTER TABLE opportunities ADD COLUMN company_confidence FLOAT DEFAULT 1.0 NOT NULL"))

            # 5. Check cosgo_runs table
            res_cosgo = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='cosgo_runs'"))
            if not res_cosgo.fetchone():
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS cosgo_runs (
                        id VARCHAR(36) PRIMARY KEY,
                        user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        budget_hours FLOAT DEFAULT 40.0 NOT NULL,
                        weekly_budget_hours FLOAT DEFAULT 10.0 NOT NULL,
                        target_roles JSON DEFAULT '[]' NOT NULL,
                        algorithm_version VARCHAR(50) DEFAULT 'cosgo-v1.0' NOT NULL,
                        status VARCHAR(50) DEFAULT 'completed' NOT NULL,
                        total_opportunities_analyzed INTEGER DEFAULT 0 NOT NULL,
                        eligible_opportunities_count INTEGER DEFAULT 0 NOT NULL,
                        excluded_opportunities_count INTEGER DEFAULT 0 NOT NULL,
                        baseline_coverage FLOAT DEFAULT 0.0 NOT NULL,
                        projected_coverage FLOAT DEFAULT 0.0 NOT NULL,
                        marginal_coverage_increase FLOAT DEFAULT 0.0 NOT NULL,
                        opportunities_at_threshold_baseline INTEGER DEFAULT 0 NOT NULL,
                        opportunities_at_threshold_projected INTEGER DEFAULT 0 NOT NULL,
                        diagnostics JSON DEFAULT '{}' NOT NULL,
                        opportunity_weights_used JSON DEFAULT '{}' NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cosgo_runs_user_id ON cosgo_runs(user_id)"))

            # 6. Check cosgo_actions table
            res_actions = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='cosgo_actions'"))
            if not res_actions.fetchone():
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS cosgo_actions (
                        id VARCHAR(36) PRIMARY KEY,
                        run_id VARCHAR(36) NOT NULL REFERENCES cosgo_runs(id) ON DELETE CASCADE,
                        user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        skill_name VARCHAR(100) NOT NULL,
                        category VARCHAR(50) DEFAULT 'technical' NOT NULL,
                        priority_rank INTEGER NOT NULL,
                        estimated_hours FLOAT NOT NULL,
                        effort_uncertainty_range JSON DEFAULT '{}' NOT NULL,
                        marginal_coverage_gain FLOAT NOT NULL,
                        cumulative_coverage FLOAT NOT NULL,
                        opportunities_count INTEGER DEFAULT 0 NOT NULL,
                        target_opportunity_ids JSON DEFAULT '[]' NOT NULL,
                        target_opportunities_summary JSON DEFAULT '[]' NOT NULL,
                        prerequisites JSON DEFAULT '[]' NOT NULL,
                        why_recommended TEXT,
                        practical_project JSON DEFAULT '{}' NOT NULL,
                        learning_resources JSON DEFAULT '[]' NOT NULL,
                        progress_state VARCHAR(50) DEFAULT 'RECOMMENDED' NOT NULL,
                        user_notes TEXT,
                        completed_at TIMESTAMP,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cosgo_actions_run_id ON cosgo_actions(run_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cosgo_actions_user_id ON cosgo_actions(user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_cosgo_actions_skill_name ON cosgo_actions(skill_name)"))

            # 7. Check outreach_drafts table
            res_drafts = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='outreach_drafts'"))
            if not res_drafts.fetchone():
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS outreach_drafts (
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
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_outreach_drafts_user_id ON outreach_drafts(user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_outreach_drafts_opportunity_id ON outreach_drafts(opportunity_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_outreach_drafts_resume_id ON outreach_drafts(resume_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_outreach_drafts_purpose ON outreach_drafts(purpose)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_outreach_drafts_generation_status ON outreach_drafts(generation_status)"))

            # 8. Check Phase 6 tables (gmail_connections, outreach_email_messages, outreach_email_replies, outreach_automation_settings)
            res_gmail = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='gmail_connections'"))
            if not res_gmail.fetchone():
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS gmail_connections (
                        id VARCHAR(36) PRIMARY KEY,
                        user_id VARCHAR(36) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                        email_address VARCHAR(255) NOT NULL,
                        encrypted_access_token TEXT,
                        encrypted_refresh_token TEXT NOT NULL,
                        token_expiry TIMESTAMP,
                        scopes JSON DEFAULT '[]' NOT NULL,
                        is_active BOOLEAN DEFAULT 1 NOT NULL,
                        last_synced_at TIMESTAMP,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_gmail_connections_email_address ON gmail_connections(email_address)"))

            res_msgs = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='outreach_email_messages'"))
            if not res_msgs.fetchone():
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS outreach_email_messages (
                        id VARCHAR(36) PRIMARY KEY,
                        user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        draft_id VARCHAR(36) REFERENCES outreach_drafts(id) ON DELETE SET NULL,
                        gmail_connection_id VARCHAR(36) REFERENCES gmail_connections(id) ON DELETE SET NULL,
                        sender_email VARCHAR(255) NOT NULL,
                        recipient_email VARCHAR(255) NOT NULL,
                        recipient_name VARCHAR(255),
                        subject VARCHAR(500) NOT NULL,
                        body TEXT NOT NULL,
                        content_hash VARCHAR(64) NOT NULL,
                        idempotency_key VARCHAR(64) NOT NULL UNIQUE,
                        status VARCHAR(50) DEFAULT 'PENDING' NOT NULL,
                        gmail_message_id VARCHAR(128),
                        gmail_thread_id VARCHAR(128),
                        error_message TEXT,
                        attempt_count INTEGER DEFAULT 0 NOT NULL,
                        sent_at TIMESTAMP,
                        has_reply BOOLEAN DEFAULT 0 NOT NULL,
                        reply_count INTEGER DEFAULT 0 NOT NULL,
                        last_reply_at TIMESTAMP,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_outreach_email_messages_user_id ON outreach_email_messages(user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_outreach_email_messages_draft_id ON outreach_email_messages(draft_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_outreach_email_messages_recipient_email ON outreach_email_messages(recipient_email)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_outreach_email_messages_content_hash ON outreach_email_messages(content_hash)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_outreach_email_messages_status ON outreach_email_messages(status)"))

            res_replies = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='outreach_email_replies'"))
            if not res_replies.fetchone():
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS outreach_email_replies (
                        id VARCHAR(36) PRIMARY KEY,
                        user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        message_id VARCHAR(36) NOT NULL REFERENCES outreach_email_messages(id) ON DELETE CASCADE,
                        gmail_message_id VARCHAR(128) NOT NULL UNIQUE,
                        gmail_thread_id VARCHAR(128) NOT NULL,
                        from_email VARCHAR(255) NOT NULL,
                        from_name VARCHAR(255),
                        subject VARCHAR(500) NOT NULL,
                        snippet TEXT,
                        body_preview TEXT,
                        received_at TIMESTAMP NOT NULL,
                        is_read BOOLEAN DEFAULT 0 NOT NULL,
                        created_at TIMESTAMP NOT NULL
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_outreach_email_replies_user_id ON outreach_email_replies(user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_outreach_email_replies_message_id ON outreach_email_replies(message_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_outreach_email_replies_thread_id ON outreach_email_replies(gmail_thread_id)"))

            res_settings = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='outreach_automation_settings'"))
            if not res_settings.fetchone():
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS outreach_automation_settings (
                        id VARCHAR(36) PRIMARY KEY,
                        user_id VARCHAR(36) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                        sending_mode VARCHAR(50) DEFAULT 'DRAFT_ONLY' NOT NULL,
                        daily_limit INTEGER DEFAULT 15 NOT NULL,
                        emails_sent_today INTEGER DEFAULT 0 NOT NULL,
                        last_limit_reset_date VARCHAR(10),
                        cooldown_minutes INTEGER DEFAULT 15 NOT NULL,
                        last_sent_at TIMESTAMP,
                        duplicate_suppression_days INTEGER DEFAULT 30 NOT NULL,
                        is_paused BOOLEAN DEFAULT 0 NOT NULL,
                        auto_followup_enabled BOOLEAN DEFAULT 0 NOT NULL,
                        followup_delay_days INTEGER DEFAULT 5 NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                """))

            # 5. Non-destructive repair for legacy contaminated job locations
            res_jobs_exist = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")).fetchone()
            if res_jobs_exist:
                import re
                city_mapping = [
                    ("greater noida", "Greater Noida"),
                    ("new delhi", "New Delhi"),
                    ("bengaluru", "Bengaluru"),
                    ("bangalore", "Bengaluru"),
                    ("gurugram", "Gurugram"),
                    ("gurgaon", "Gurugram"),
                    ("hyderabad", "Hyderabad"),
                    ("noida", "Noida"),
                    ("delhi", "Delhi"),
                    ("mumbai", "Mumbai"),
                    ("pune", "Pune"),
                    ("chennai", "Chennai"),
                    ("kolkata", "Kolkata"),
                    ("mohali", "Mohali"),
                    ("chandigarh", "Chandigarh"),
                    ("jaipur", "Jaipur"),
                    ("ahmedabad", "Ahmedabad"),
                    ("kochi", "Kochi"),
                    ("lucknow", "Lucknow"),
                    ("indore", "Indore"),
                    ("coimbatore", "Coimbatore"),
                    ("visakhapatnam", "Visakhapatnam"),
                ]
                job_rows = conn.execute(text("SELECT id, title, location, primary_url, description FROM jobs")).fetchall()
                for j_row in job_rows:
                    jid, jtitle, jloc, jurl, jdesc = j_row
                    combined = f"{jtitle or ''} {jdesc or ''} {jurl or ''}".lower()
                    matched_loc = None
                    for term, canonical_name in city_mapping:
                        if re.search(r"\b" + re.escape(term) + r"\b", combined):
                            matched_loc = canonical_name
                            break
                    if not matched_loc and ("remote" in combined or "work from home" in combined or "wfh" in combined):
                        matched_loc = "Remote"
                    if matched_loc and (not jloc or matched_loc.lower() != jloc.lower()):
                        conn.execute(
                            text("UPDATE jobs SET location = :new_loc WHERE id = :jid"),
                            {"new_loc": matched_loc, "jid": jid}
                        )
                    elif jloc and jloc.lower() in ("bangalore", "bengaluru") and jloc != "Bengaluru":
                        conn.execute(text("UPDATE jobs SET location = 'Bengaluru' WHERE id = :jid"), {"jid": jid})
                    elif jloc and jloc.lower() in ("gurgaon", "gurugram") and jloc != "Gurugram":
                        conn.execute(text("UPDATE jobs SET location = 'Gurugram' WHERE id = :jid"), {"jid": jid})
    except Exception:
        pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

