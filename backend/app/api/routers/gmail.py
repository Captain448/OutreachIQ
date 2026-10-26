import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.gmail import (
    GmailConnection,
    OutreachEmailMessage,
    OutreachEmailReply,
    OutreachAutomationSettings,
    EmailMessageStatus,
    SendingMode
)
from app.schemas.gmail import (
    GmailConnectionResponse,
    GmailOAuthUrlResponse,
    GmailOAuthCallbackRequest,
    OutreachEmailPreviewRequest,
    OutreachEmailPreviewResponse,
    OutreachEmailSendRequest,
    OutreachEmailMessageResponse,
    OutreachEmailReplyResponse,
    OutreachAutomationSettingsUpdate,
    OutreachAutomationSettingsResponse,
    ReplySyncResponse
)
from app.services.gmail_service import (
    GmailService,
    GmailAuthError,
    GmailSendError
)
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["gmail"])


# --- 1. OAuth & Account Management ---

@router.get("/connection", response_model=Optional[GmailConnectionResponse])
def get_gmail_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves the authenticated user's connected Gmail account status.
    Returns null if no account is connected. Never leaks tokens.
    """
    conn = db.query(GmailConnection).filter(
        GmailConnection.user_id == current_user.id,
        GmailConnection.is_active == True
    ).first()
    return conn


@router.get("/oauth/url", response_model=GmailOAuthUrlResponse)
def get_oauth_authorization_url(
    current_user: User = Depends(get_current_user)
):
    """
    Generates a secure, CSRF-protected Google OAuth 2.0 authorization URL.
    The state parameter is cryptographically signed and scoped to current_user.
    """
    auth_url, state = GmailService.get_authorization_url(current_user.id)
    return GmailOAuthUrlResponse(authorization_url=auth_url, state=state)


@router.post("/oauth/callback", response_model=GmailConnectionResponse)
def handle_oauth_callback(
    payload: GmailOAuthCallbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Completes OAuth code exchange after user authorizes Gmail access.
    Validates state signature, fetches verified email, encrypts tokens, and stores connection.
    """
    # 1. State CSRF and User Verification
    if not GmailService.verify_oauth_state(payload.state, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or forged OAuth state parameter. Please restart authorization."
        )

    # 2. Token Exchange
    try:
        tokens = GmailService.exchange_code(payload.code)
    except GmailAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")
    expires_in = tokens.get("expires_in", 3600)
    scopes = tokens.get("scope", "").split() if isinstance(tokens.get("scope"), str) else []

    if not refresh_token and not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth response did not include authorization tokens."
        )

    # 3. Fetch Verified Account Email
    try:
        account_email = GmailService.fetch_account_email(access_token)
    except GmailAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # 4. Save Encrypted Connection
    conn = GmailService.save_or_update_connection(
        db=db,
        user_id=current_user.id,
        email_address=account_email,
        refresh_token=refresh_token or "mock_refresh_token",
        access_token=access_token,
        expires_in=expires_in,
        scopes=scopes
    )

    return conn


@router.post("/disconnect", status_code=status.HTTP_200_OK)
def disconnect_gmail(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Revokes authorization tokens with Google and removes the stored connection.
    """
    GmailService.disconnect_account(db, current_user.id)
    return {"status": "disconnected", "message": "Gmail account disconnected successfully."}


# --- 2. Email Preview & Sending ---

@router.post("/preview", response_model=OutreachEmailPreviewResponse)
def preview_outreach_email(
    payload: OutreachEmailPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Produces a safe, grounded preview of the message before sending.
    Generates the cryptographic content_hash required for subsequent send authorization.
    """
    try:
        preview = GmailService.preview_email(
            db=db,
            user_id=current_user.id,
            draft_id=payload.draft_id,
            recipient_email=payload.recipient_email,
            recipient_name=payload.recipient_name,
            subject=payload.subject,
            body=payload.body
        )
        return OutreachEmailPreviewResponse(**preview)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))


@router.post("/send", response_model=OutreachEmailMessageResponse, status_code=status.HTTP_200_OK)
def send_outreach_email(
    payload: OutreachEmailSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sends an approved outreach email through the connected Gmail account.
    Enforces content hash verification, duplicate suppression, daily limits, and cooldowns.
    """
    try:
        sent_record = GmailService.send_outreach_email(
            db=db,
            user_id=current_user.id,
            draft_id=payload.draft_id,
            recipient_email=payload.recipient_email,
            recipient_name=payload.recipient_name,
            subject=payload.subject,
            body=payload.body,
            approved_content_hash=payload.approved_content_hash,
            idempotency_key=payload.idempotency_key,
            allow_recent_duplicate=payload.allow_recent_duplicate
        )
        return sent_record
    except GmailSendError as send_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(send_err))
    except GmailAuthError as auth_err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(auth_err))


# --- 3. Message History & Replies ---

@router.get("/messages", response_model=List[OutreachEmailMessageResponse])
def get_sent_messages(
    limit: int = Query(50, ge=1, le=100),
    draft_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves sending history for the authenticated user, ordered by creation date descending.
    """
    query = (
        db.query(OutreachEmailMessage)
        .filter(OutreachEmailMessage.user_id == current_user.id)
    )
    if draft_id:
        query = query.filter(OutreachEmailMessage.draft_id == draft_id)

    return query.order_by(OutreachEmailMessage.created_at.desc()).limit(limit).all()


@router.get("/messages/{message_id}", response_model=OutreachEmailMessageResponse)
def get_sent_message(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves a specific sent outreach message record. Enforces user isolation.
    """
    msg = db.query(OutreachEmailMessage).filter(
        OutreachEmailMessage.id == message_id,
        OutreachEmailMessage.user_id == current_user.id
    ).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message record not found.")
    return msg


@router.get("/replies", response_model=List[OutreachEmailReplyResponse])
def get_replies(
    message_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves detected replies associated with the candidate's outreach.
    """
    query = db.query(OutreachEmailReply).filter(OutreachEmailReply.user_id == current_user.id)
    if message_id:
        query = query.filter(OutreachEmailReply.message_id == message_id)

    return query.order_by(OutreachEmailReply.received_at.desc()).limit(limit).all()


@router.post("/replies/sync", response_model=ReplySyncResponse)
def sync_replies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Initiates a bounded, targeted poll of Gmail threads associated with OutReachIQ messages.
    Records new replies and suppresses automated follow-up sequences.
    """
    res = GmailService.sync_replies_for_user(db, current_user.id)
    return ReplySyncResponse(**res)


# --- 4. Controlled Autonomy Settings ---

@router.get("/settings", response_model=OutreachAutomationSettingsResponse)
def get_automation_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves user's outreach autonomy settings (mode, daily limits, cooldowns, pause state).
    """
    return GmailService.get_or_create_settings(db, current_user.id)


@router.put("/settings", response_model=OutreachAutomationSettingsResponse)
@router.patch("/settings", response_model=OutreachAutomationSettingsResponse)
def update_automation_settings(
    payload: OutreachAutomationSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates outreach autonomy settings.
    Default mode is DRAFT_ONLY; AUTO_SEND_OPT_IN requires explicit opt-in.
    """
    st = GmailService.get_or_create_settings(db, current_user.id)

    if payload.sending_mode is not None:
        st.sending_mode = payload.sending_mode
    if payload.daily_limit is not None:
        st.daily_limit = payload.daily_limit
    if payload.cooldown_minutes is not None:
        st.cooldown_minutes = payload.cooldown_minutes
    if payload.duplicate_suppression_days is not None:
        st.duplicate_suppression_days = payload.duplicate_suppression_days
    if payload.is_paused is not None:
        st.is_paused = payload.is_paused
    if payload.auto_followup_enabled is not None:
        st.auto_followup_enabled = payload.auto_followup_enabled
    if payload.followup_delay_days is not None:
        st.followup_delay_days = payload.followup_delay_days

    db.commit()
    db.refresh(st)
    return st
