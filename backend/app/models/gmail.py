import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.orm import relationship
from app.db.session import Base


class EmailMessageStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


class SendingMode(str, enum.Enum):
    DRAFT_ONLY = "DRAFT_ONLY"
    REVIEW_BEFORE_SEND = "REVIEW_BEFORE_SEND"
    AUTO_SEND_OPT_IN = "AUTO_SEND_OPT_IN"


class GmailConnection(Base):
    __tablename__ = "gmail_connections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    email_address = Column(String(255), nullable=False)
    encrypted_access_token = Column(Text, nullable=True)
    encrypted_refresh_token = Column(Text, nullable=False)
    token_expiry = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(JSON, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship("User", back_populates="gmail_connection")
    messages = relationship("OutreachEmailMessage", back_populates="gmail_connection")

    def __repr__(self) -> str:
        return f"<GmailConnection id={self.id} user_id={self.user_id} email={self.email_address} is_active={self.is_active}>"


class OutreachEmailMessage(Base):
    __tablename__ = "outreach_email_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    draft_id = Column(String(36), ForeignKey("outreach_drafts.id", ondelete="SET NULL"), nullable=True, index=True)
    gmail_connection_id = Column(String(36), ForeignKey("gmail_connections.id", ondelete="SET NULL"), nullable=True, index=True)

    sender_email = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False, index=True)
    recipient_name = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)

    content_hash = Column(String(64), nullable=False, index=True)
    idempotency_key = Column(String(64), nullable=False, unique=True, index=True)

    status = Column(
        Enum(EmailMessageStatus, native_enum=False),
        default=EmailMessageStatus.PENDING,
        nullable=False,
        index=True
    )
    gmail_message_id = Column(String(128), nullable=True, index=True)
    gmail_thread_id = Column(String(128), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    has_reply = Column(Boolean, default=False, nullable=False)
    reply_count = Column(Integer, default=0, nullable=False)
    last_reply_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship("User", back_populates="outreach_messages")
    draft = relationship("OutreachDraft", back_populates="sent_messages")
    gmail_connection = relationship("GmailConnection", back_populates="messages")
    replies = relationship("OutreachEmailReply", back_populates="parent_message", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<OutreachEmailMessage id={self.id} recipient={self.recipient_email} status={self.status}>"


class OutreachEmailReply(Base):
    __tablename__ = "outreach_email_replies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(String(36), ForeignKey("outreach_email_messages.id", ondelete="CASCADE"), nullable=False, index=True)

    gmail_message_id = Column(String(128), nullable=False, unique=True, index=True)
    gmail_thread_id = Column(String(128), nullable=False, index=True)

    from_email = Column(String(255), nullable=False)
    from_name = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=False)
    snippet = Column(Text, nullable=True)
    body_preview = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="outreach_replies")
    parent_message = relationship("OutreachEmailMessage", back_populates="replies")

    def __repr__(self) -> str:
        return f"<OutreachEmailReply id={self.id} from={self.from_email} thread={self.gmail_thread_id}>"


class OutreachAutomationSettings(Base):
    __tablename__ = "outreach_automation_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    sending_mode = Column(
        Enum(SendingMode, native_enum=False),
        default=SendingMode.DRAFT_ONLY,
        nullable=False,
        index=True
    )
    daily_limit = Column(Integer, default=15, nullable=False)
    emails_sent_today = Column(Integer, default=0, nullable=False)
    last_limit_reset_date = Column(String(10), nullable=True)
    cooldown_minutes = Column(Integer, default=15, nullable=False)
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    duplicate_suppression_days = Column(Integer, default=30, nullable=False)
    is_paused = Column(Boolean, default=False, nullable=False)
    auto_followup_enabled = Column(Boolean, default=False, nullable=False)
    followup_delay_days = Column(Integer, default=5, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship("User", back_populates="outreach_automation_settings")

    def __repr__(self) -> str:
        return f"<OutreachAutomationSettings user_id={self.user_id} mode={self.sending_mode} paused={self.is_paused}>"
