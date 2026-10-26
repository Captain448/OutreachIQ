from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

from app.models.gmail import EmailMessageStatus, SendingMode


class GmailConnectionResponse(BaseModel):
    id: str
    user_id: str
    email_address: str
    is_active: bool
    scopes: List[str]
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GmailOAuthUrlResponse(BaseModel):
    authorization_url: str
    state: str


class GmailOAuthCallbackRequest(BaseModel):
    code: str
    state: str


class OutreachEmailPreviewRequest(BaseModel):
    draft_id: str
    recipient_email: str
    recipient_name: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class OutreachEmailPreviewResponse(BaseModel):
    draft_id: str
    sender_email: str
    recipient_email: str
    recipient_name: Optional[str] = None
    subject: str
    body: str
    content_hash: str
    is_connected: bool
    can_send: bool
    warnings: List[str] = Field(default_factory=list)


class OutreachEmailSendRequest(BaseModel):
    draft_id: str
    recipient_email: str
    recipient_name: Optional[str] = None
    subject: str
    body: str
    approved_content_hash: str
    idempotency_key: Optional[str] = None
    allow_recent_duplicate: bool = False


class OutreachEmailMessageResponse(BaseModel):
    id: str
    user_id: str
    draft_id: Optional[str] = None
    sender_email: str
    recipient_email: str
    recipient_name: Optional[str] = None
    subject: str
    body: str
    content_hash: str
    idempotency_key: str
    status: EmailMessageStatus
    gmail_message_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    error_message: Optional[str] = None
    attempt_count: int
    sent_at: Optional[datetime] = None
    has_reply: bool
    reply_count: int
    last_reply_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OutreachEmailReplyResponse(BaseModel):
    id: str
    message_id: str
    gmail_message_id: str
    gmail_thread_id: str
    from_email: str
    from_name: Optional[str] = None
    subject: str
    snippet: Optional[str] = None
    body_preview: Optional[str] = None
    received_at: datetime
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OutreachAutomationSettingsUpdate(BaseModel):
    sending_mode: Optional[SendingMode] = None
    daily_limit: Optional[int] = Field(None, ge=1, le=100)
    cooldown_minutes: Optional[int] = Field(None, ge=1, le=1440)
    duplicate_suppression_days: Optional[int] = Field(None, ge=1, le=365)
    is_paused: Optional[bool] = None
    auto_followup_enabled: Optional[bool] = None
    followup_delay_days: Optional[int] = Field(None, ge=1, le=60)


class OutreachAutomationSettingsResponse(BaseModel):
    id: str
    user_id: str
    sending_mode: SendingMode
    daily_limit: int
    emails_sent_today: int
    cooldown_minutes: int
    last_sent_at: Optional[datetime] = None
    duplicate_suppression_days: int
    is_paused: bool
    auto_followup_enabled: bool
    followup_delay_days: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReplySyncResponse(BaseModel):
    synced_threads_count: int
    new_replies_count: int
    status: str
    last_synced_at: datetime
