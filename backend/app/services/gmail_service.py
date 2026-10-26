import os
import json
import base64
import hmac
import hashlib
import email
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple, List
import logging
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.gmail import (
    GmailConnection,
    OutreachEmailMessage,
    OutreachEmailReply,
    OutreachAutomationSettings,
    EmailMessageStatus,
    SendingMode
)
from app.models.outreach import OutreachDraft
from app.services.encryption_service import TokenEncryptionService, EncryptionError

logger = logging.getLogger(__name__)


class GmailAuthError(Exception):
    """Raised on authentication, token, or consent errors."""
    pass


class GmailSendError(Exception):
    """Raised when email transmission fails."""
    pass


class GmailTimeoutError(Exception):
    """Raised when Gmail API call times out with outcome unknown."""
    pass


class MockGmailClient:
    """
    Hermetic test harness for simulating Gmail OAuth, email sending, and reply monitoring
    without needing live external Google API credentials.
    """
    simulated_outcome_unknown: bool = False
    simulated_send_error: Optional[str] = None
    simulated_replies: List[Dict[str, Any]] = []

    @classmethod
    def reset(cls) -> None:
        cls.simulated_outcome_unknown = False
        cls.simulated_send_error = None
        cls.simulated_replies = []

    @classmethod
    def exchange_code(cls, code: str) -> Dict[str, Any]:
        if code == "invalid_code" or code == "revoked_code":
            raise GmailAuthError("Invalid authorization code or consent denied.")
        return {
            "access_token": f"mock_access_token_{code}",
            "refresh_token": f"mock_refresh_token_{code}",
            "expires_in": 3600,
            "scope": " ".join(settings.GMAIL_SCOPES),
            "token_type": "Bearer"
        }

    @classmethod
    def refresh_token(cls, refresh_token: str) -> Dict[str, Any]:
        if "revoked" in refresh_token:
            raise GmailAuthError("Refresh token revoked by user.")
        return {
            "access_token": f"mock_refreshed_access_{hashlib.md5(refresh_token.encode()).hexdigest()[:8]}",
            "expires_in": 3600,
            "token_type": "Bearer"
        }

    @classmethod
    def fetch_userinfo(cls, access_token: str) -> Dict[str, Any]:
        return {
            "email": "candidate.verified@example.com",
            "verified_email": True,
            "name": "Candidate Verified"
        }

    @classmethod
    def send_message(cls, access_token: str, raw_b64: str) -> Dict[str, Any]:
        if cls.simulated_outcome_unknown:
            raise GmailTimeoutError("Gmail API connection timed out. Message delivery state is unknown.")
        if cls.simulated_send_error:
            raise GmailSendError(cls.simulated_send_error)

        msg_hash = hashlib.sha256(raw_b64.encode()).hexdigest()[:12]
        return {
            "id": f"gmsg_{msg_hash}",
            "threadId": f"gthread_{msg_hash}",
            "labelIds": ["SENT"]
        }

    @classmethod
    def get_thread(cls, access_token: str, thread_id: str) -> Dict[str, Any]:
        return {
            "id": thread_id,
            "messages": cls.simulated_replies
        }


class GmailService:
    """
    Comprehensive service for managing Google OAuth, token lifecycle,
    evidence-grounded email dispatching, and targeted reply monitoring.
    """

    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    GMAIL_THREADS_URL = "https://gmail.googleapis.com/gmail/v1/users/me/threads"

    # --- 1. OAuth Workflow ---

    @classmethod
    def generate_oauth_state(cls, user_id: str) -> str:
        """
        Generates a tamper-proof signed OAuth state parameter including user_id,
        timestamp, and an HMAC signature.
        """
        timestamp = int(datetime.now(timezone.utc).timestamp())
        random_nonce = os.urandom(8).hex()
        payload = f"{user_id}:{timestamp}:{random_nonce}"
        sig = hmac.new(
            settings.JWT_SECRET.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        raw = f"{payload}:{sig}"
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")

    @classmethod
    def verify_oauth_state(cls, state_b64: str, expected_user_id: str) -> bool:
        """
        Validates the OAuth state signature, expiry window (15 minutes), and user isolation.
        """
        try:
            raw = base64.urlsafe_b64decode(state_b64.encode("utf-8")).decode("utf-8")
            parts = raw.split(":")
            if len(parts) != 4:
                return False
            user_id, timestamp_str, nonce, sig = parts
            if user_id != expected_user_id:
                return False

            payload = f"{user_id}:{timestamp_str}:{nonce}"
            expected_sig = hmac.new(
                settings.JWT_SECRET.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(sig, expected_sig):
                return False

            timestamp = int(timestamp_str)
            now = int(datetime.now(timezone.utc).timestamp())
            if now - timestamp > 900:  # 15 minute expiration
                return False

            return True
        except Exception:
            return False

    @classmethod
    def get_authorization_url(cls, user_id: str) -> Tuple[str, str]:
        """
        Constructs the Google OAuth 2.0 authorization URL.
        """
        state = cls.generate_oauth_state(user_id)
        client_id = settings.GOOGLE_CLIENT_ID or "mock-client-id.apps.googleusercontent.com"
        scopes = "%20".join([httpx.URL(s).raw_path.decode() if "://" in s else s for s in settings.GMAIL_SCOPES])
        redirect_uri = settings.GOOGLE_REDIRECT_URI

        auth_url = (
            f"{cls.GOOGLE_AUTH_URL}?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope={scopes}&"
            f"access_type=offline&"
            f"prompt=consent&"
            f"state={state}"
        )
        return auth_url, state

    @classmethod
    def exchange_code(cls, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """
        Exchanges authorization code for access and refresh tokens.
        Uses MockGmailClient when live client credentials are not configured.
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET or settings.ENVIRONMENT == "test":
            return MockGmailClient.exchange_code(code)

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(
                    cls.GOOGLE_TOKEN_URL,
                    data={
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri or settings.GOOGLE_REDIRECT_URI,
                    }
                )
                if res.status_code != 200:
                    err_msg = res.json().get("error_description", res.text)
                    raise GmailAuthError(f"OAuth token exchange failed: {err_msg}")
                return res.json()
        except Exception as exc:
            if isinstance(exc, GmailAuthError):
                raise
            raise GmailAuthError(f"Network error during OAuth token exchange: {str(exc)}") from exc

    @classmethod
    def fetch_account_email(cls, access_token: str) -> str:
        """
        Retrieves the authenticated Gmail account email address.
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET or settings.ENVIRONMENT == "test":
            return MockGmailClient.fetch_userinfo(access_token)["email"]

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(
                    cls.GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                if res.status_code != 200:
                    raise GmailAuthError(f"Failed to fetch Google user profile: {res.text}")
                data = res.json()
                email_addr = data.get("email")
                if not email_addr:
                    raise GmailAuthError("No verified email address returned in Google OAuth profile.")
                return email_addr
        except Exception as exc:
            if isinstance(exc, GmailAuthError):
                raise
            raise GmailAuthError(f"Network error fetching user profile: {str(exc)}") from exc

    @classmethod
    def save_or_update_connection(
        cls,
        db: Session,
        user_id: str,
        email_address: str,
        refresh_token: str,
        access_token: Optional[str] = None,
        expires_in: int = 3600,
        scopes: Optional[List[str]] = None
    ) -> GmailConnection:
        """
        Encrypts refresh/access tokens and persists the Gmail connection for the user.
        """
        enc_refresh = TokenEncryptionService.encrypt(refresh_token)
        enc_access = TokenEncryptionService.encrypt(access_token) if access_token else None
        token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        conn = db.query(GmailConnection).filter(GmailConnection.user_id == user_id).first()
        if conn:
            conn.email_address = email_address
            conn.encrypted_refresh_token = enc_refresh
            conn.encrypted_access_token = enc_access
            conn.token_expiry = token_expiry
            conn.scopes = scopes or settings.GMAIL_SCOPES
            conn.is_active = True
            conn.updated_at = datetime.now(timezone.utc)
        else:
            conn = GmailConnection(
                user_id=user_id,
                email_address=email_address,
                encrypted_refresh_token=enc_refresh,
                encrypted_access_token=enc_access,
                token_expiry=token_expiry,
                scopes=scopes or settings.GMAIL_SCOPES,
                is_active=True
            )
            db.add(conn)

        db.commit()
        db.refresh(conn)
        return conn

    @classmethod
    def get_valid_access_token(cls, db: Session, user_id: str) -> Tuple[str, GmailConnection]:
        """
        Retrieves a decrypted, non-expired access token. Refreshes via Google OAuth if expired.
        """
        conn = db.query(GmailConnection).filter(GmailConnection.user_id == user_id).first()
        if not conn or not conn.is_active:
            raise GmailAuthError("No active Gmail connection found. Please connect your account first.")

        now_utc = datetime.now(timezone.utc)
        # Check if existing access token is still valid (with 5-minute buffer)
        if conn.encrypted_access_token and conn.token_expiry and conn.token_expiry > now_utc + timedelta(minutes=5):
            try:
                decrypted_access = TokenEncryptionService.decrypt(conn.encrypted_access_token)
                return decrypted_access, conn
            except EncryptionError:
                logger.warning("Failed to decrypt access token; attempting refresh.")

        # Access token missing or expired; refresh with refresh token
        decrypted_refresh = TokenEncryptionService.decrypt(conn.encrypted_refresh_token)

        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET or settings.ENVIRONMENT == "test":
            refreshed = MockGmailClient.refresh_token(decrypted_refresh)
        else:
            try:
                with httpx.Client(timeout=15.0) as client:
                    res = client.post(
                        cls.GOOGLE_TOKEN_URL,
                        data={
                            "client_id": settings.GOOGLE_CLIENT_ID,
                            "client_secret": settings.GOOGLE_CLIENT_SECRET,
                            "refresh_token": decrypted_refresh,
                            "grant_type": "refresh_token"
                        }
                    )
                    if res.status_code != 200:
                        # Mark connection as inactive if revoked
                        conn.is_active = False
                        db.commit()
                        raise GmailAuthError(f"OAuth refresh failed. Access may have been revoked: {res.text}")
                    refreshed = res.json()
            except Exception as exc:
                if isinstance(exc, GmailAuthError):
                    raise
                raise GmailAuthError(f"Network error refreshing access token: {str(exc)}") from exc

        new_access = refreshed["access_token"]
        expires_in = refreshed.get("expires_in", 3600)
        conn.encrypted_access_token = TokenEncryptionService.encrypt(new_access)
        conn.token_expiry = now_utc + timedelta(seconds=expires_in)
        conn.updated_at = now_utc
        db.commit()
        db.refresh(conn)

        return new_access, conn

    @classmethod
    def disconnect_account(cls, db: Session, user_id: str) -> bool:
        """
        Revokes token with Google and removes or deactivates the stored connection.
        """
        conn = db.query(GmailConnection).filter(GmailConnection.user_id == user_id).first()
        if not conn:
            return True

        try:
            refresh_token = TokenEncryptionService.decrypt(conn.encrypted_refresh_token)
            if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET and settings.ENVIRONMENT != "test":
                with httpx.Client(timeout=10.0) as client:
                    client.post(cls.GOOGLE_REVOKE_URL, params={"token": refresh_token})
        except Exception as e:
            logger.warning(f"Google token revocation request returned: {str(e)}")

        db.delete(conn)
        db.commit()
        return True

    # --- 2. Hashing & Safeguards ---

    @classmethod
    def compute_content_hash(cls, recipient_email: str, subject: str, body: str) -> str:
        """
        Produces a deterministic SHA-256 fingerprint of the reviewed recipient and message content.
        Any modification to recipient, subject, or body after preview invalidates this hash.
        """
        canonical = f"{recipient_email.strip().lower()}|{subject.strip()}|{body.strip()}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def generate_idempotency_key(
        cls,
        user_id: str,
        draft_id: str,
        recipient_email: str,
        content_hash: str
    ) -> str:
        """
        Computes a unique idempotency key to prevent accidental duplicate transmissions.
        """
        raw = f"{user_id}:{draft_id}:{recipient_email.strip().lower()}:{content_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # --- 3. Automation Settings & Policy Checks ---

    @classmethod
    def get_or_create_settings(cls, db: Session, user_id: str) -> OutreachAutomationSettings:
        """
        Retrieves user's automation settings or initializes safe defaults:
        - sending_mode = DRAFT_ONLY
        - daily_limit = 15
        - cooldown_minutes = 15
        - duplicate_suppression_days = 30
        - is_paused = False
        """
        st = db.query(OutreachAutomationSettings).filter(OutreachAutomationSettings.user_id == user_id).first()
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not st:
            st = OutreachAutomationSettings(
                user_id=user_id,
                sending_mode=SendingMode.DRAFT_ONLY,
                daily_limit=settings.OUTREACH_DEFAULT_DAILY_LIMIT,
                cooldown_minutes=settings.OUTREACH_DEFAULT_COOLDOWN_MINUTES,
                duplicate_suppression_days=settings.OUTREACH_DUPLICATE_SUPPRESSION_DAYS,
                is_paused=False,
                auto_followup_enabled=False,
                followup_delay_days=5,
                emails_sent_today=0,
                last_limit_reset_date=today_str
            )
            db.add(st)
            db.commit()
            db.refresh(st)
        else:
            # Check if daily counter needs resetting based on UTC date
            if st.last_limit_reset_date != today_str:
                st.emails_sent_today = 0
                st.last_limit_reset_date = today_str
                db.commit()
                db.refresh(st)

        return st

    # --- 4. Preview & Send Operations ---

    @classmethod
    def preview_email(
        cls,
        db: Session,
        user_id: str,
        draft_id: str,
        recipient_email: str,
        recipient_name: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a preview of the email to be sent, calculates the approved content hash,
        and evaluates safety warnings (duplicate checks, limits, connection status).
        """
        draft = db.query(OutreachDraft).filter(OutreachDraft.id == draft_id, OutreachDraft.user_id == user_id).first()
        if not draft:
            raise ValueError("Outreach draft not found or access denied.")

        final_subject = (subject if subject is not None else draft.subject).strip()
        final_body = (body if body is not None else draft.body).strip()
        final_recipient = recipient_email.strip().lower()

        content_hash = cls.compute_content_hash(final_recipient, final_subject, final_body)

        conn = db.query(GmailConnection).filter(GmailConnection.user_id == user_id, GmailConnection.is_active == True).first()
        aut_settings = cls.get_or_create_settings(db, user_id)

        warnings: List[str] = []
        can_send = True

        if not conn:
            warnings.append("No active Gmail account connected. Connect Gmail to send.")
            can_send = False

        if aut_settings.is_paused:
            warnings.append("Outreach sending is currently PAUSED in your settings.")
            can_send = False

        if aut_settings.sending_mode == SendingMode.DRAFT_ONLY:
            warnings.append("Sending mode is currently set to 'Draft Only'. Change mode to 'Review Before Send' to enable sending.")
            can_send = False

        if aut_settings.emails_sent_today >= aut_settings.daily_limit:
            warnings.append(f"Daily sending limit ({aut_settings.daily_limit} emails) reached for today.")
            can_send = False

        now_utc = datetime.now(timezone.utc)
        if aut_settings.last_sent_at:
            last_sent = aut_settings.last_sent_at
            if last_sent.tzinfo is None:
                last_sent = last_sent.replace(tzinfo=timezone.utc)
            elapsed = (now_utc - last_sent).total_seconds() / 60.0
            if elapsed < aut_settings.cooldown_minutes:
                rem = int(aut_settings.cooldown_minutes - elapsed)
                warnings.append(f"In cooldown period ({rem} minutes remaining before next send).")

        # Check duplicate suppression
        cutoff = now_utc - timedelta(days=aut_settings.duplicate_suppression_days)
        cutoff_naive = cutoff.replace(tzinfo=None)
        recent_sent = (
            db.query(OutreachEmailMessage)
            .filter(
                OutreachEmailMessage.user_id == user_id,
                OutreachEmailMessage.recipient_email == final_recipient,
                OutreachEmailMessage.status == EmailMessageStatus.SENT,
                (OutreachEmailMessage.sent_at >= cutoff) | (OutreachEmailMessage.sent_at >= cutoff_naive)
            )
            .first()
        )
        if recent_sent:
            warnings.append(
                f"You have already sent an outreach email to {final_recipient} within the last {aut_settings.duplicate_suppression_days} days."
            )

        return {
            "draft_id": draft.id,
            "sender_email": conn.email_address if conn else "",
            "recipient_email": final_recipient,
            "recipient_name": recipient_name or draft.recipient_name,
            "subject": final_subject,
            "body": final_body,
            "content_hash": content_hash,
            "is_connected": conn is not None,
            "can_send": can_send,
            "warnings": warnings
        }

    @classmethod
    def send_outreach_email(
        cls,
        db: Session,
        user_id: str,
        draft_id: str,
        recipient_email: str,
        recipient_name: Optional[str],
        subject: str,
        body: str,
        approved_content_hash: str,
        idempotency_key: Optional[str] = None,
        allow_recent_duplicate: bool = False
    ) -> OutreachEmailMessage:
        """
        Sends an approved outreach email through Gmail API with strict safeguards:
        - Validates content hash against approved preview.
        - Enforces idempotency and duplicate suppression.
        - Enforces daily limits and cooldowns.
        - Handles ambiguous timeouts gracefully without blind retry.
        """
        clean_recipient = recipient_email.strip().lower()
        clean_subject = subject.strip()
        clean_body = body.strip()

        # 1. Content Hash Verification
        current_hash = cls.compute_content_hash(clean_recipient, clean_subject, clean_body)
        if current_hash != approved_content_hash:
            raise GmailSendError(
                "Content has changed since your preview approval. Please review and confirm the updated message."
            )

        # 2. Basic email validation
        if "@" not in clean_recipient or "." not in clean_recipient.split("@")[-1]:
            raise GmailSendError("Invalid recipient email address.")

        # 3. Draft Ownership
        draft = db.query(OutreachDraft).filter(OutreachDraft.id == draft_id, OutreachDraft.user_id == user_id).first()
        if not draft:
            raise GmailSendError("Outreach draft not found or access denied.")

        # 4. Automation Settings & Limits
        aut_settings = cls.get_or_create_settings(db, user_id)
        if aut_settings.is_paused:
            raise GmailSendError("Outreach sending is currently paused in your automation settings.")
        if aut_settings.sending_mode == SendingMode.DRAFT_ONLY:
            raise GmailSendError("Sending mode is set to 'Draft Only'. Change mode to authorize sending.")
        if aut_settings.emails_sent_today >= aut_settings.daily_limit:
            raise GmailSendError(f"Daily sending limit ({aut_settings.daily_limit}) reached.")

        now_utc = datetime.now(timezone.utc)
        if aut_settings.last_sent_at:
            last_sent = aut_settings.last_sent_at
            if last_sent.tzinfo is None:
                last_sent = last_sent.replace(tzinfo=timezone.utc)
            elapsed = (now_utc - last_sent).total_seconds() / 60.0
            if elapsed < aut_settings.cooldown_minutes:
                rem = int(aut_settings.cooldown_minutes - elapsed)
                raise GmailSendError(f"Cooldown active: please wait {rem} more minutes before sending.")

        # 5. Duplicate Suppression Check
        if not allow_recent_duplicate:
            cutoff = now_utc - timedelta(days=aut_settings.duplicate_suppression_days)
            cutoff_naive = cutoff.replace(tzinfo=None)
            recent_sent = (
                db.query(OutreachEmailMessage)
                .filter(
                    OutreachEmailMessage.user_id == user_id,
                    OutreachEmailMessage.recipient_email == clean_recipient,
                    OutreachEmailMessage.status == EmailMessageStatus.SENT,
                    (OutreachEmailMessage.sent_at >= cutoff) | (OutreachEmailMessage.sent_at >= cutoff_naive)
                )
                .first()
            )
            if recent_sent:
                raise GmailSendError(
                    f"An outreach email was already sent to {clean_recipient} in the last {aut_settings.duplicate_suppression_days} days. "
                    "Confirm recent duplicate send to proceed."
                )

        # 6. Idempotency Check
        idemp = idempotency_key or cls.generate_idempotency_key(user_id, draft_id, clean_recipient, current_hash)
        existing_msg = db.query(OutreachEmailMessage).filter(OutreachEmailMessage.idempotency_key == idemp).first()
        if existing_msg:
            if existing_msg.status == EmailMessageStatus.SENT:
                raise GmailSendError("This exact message has already been sent successfully.")
            elif existing_msg.status == EmailMessageStatus.SENDING:
                raise GmailSendError("Message sending is currently in progress.")

        # 7. Get Valid Credentials
        access_token, conn = cls.get_valid_access_token(db, user_id)

        # 8. Create Outbound Message Record
        if not existing_msg:
            msg_record = OutreachEmailMessage(
                user_id=user_id,
                draft_id=draft.id,
                gmail_connection_id=conn.id,
                sender_email=conn.email_address,
                recipient_email=clean_recipient,
                recipient_name=recipient_name or draft.recipient_name,
                subject=clean_subject,
                body=clean_body,
                content_hash=current_hash,
                idempotency_key=idemp,
                status=EmailMessageStatus.SENDING,
                attempt_count=1
            )
            db.add(msg_record)
        else:
            msg_record = existing_msg
            msg_record.status = EmailMessageStatus.SENDING
            msg_record.attempt_count += 1
            msg_record.updated_at = now_utc

        db.commit()
        db.refresh(msg_record)

        # 9. Build RFC 2822 / MIME Message
        mime_msg = MIMEText(clean_body, "plain", "utf-8")
        mime_msg["To"] = clean_recipient
        mime_msg["From"] = conn.email_address
        mime_msg["Subject"] = clean_subject
        raw_b64 = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")

        # 10. Execute Send via Gmail API
        try:
            if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET or settings.ENVIRONMENT == "test":
                result = MockGmailClient.send_message(access_token, raw_b64)
            else:
                with httpx.Client(timeout=15.0) as http_client:
                    res = http_client.post(
                        cls.GMAIL_SEND_URL,
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json"
                        },
                        json={"raw": raw_b64}
                    )
                    if res.status_code != 200:
                        err_text = res.text
                        raise GmailSendError(f"Gmail API error ({res.status_code}): {err_text}")
                    result = res.json()

            # Success
            msg_record.status = EmailMessageStatus.SENT
            msg_record.gmail_message_id = result.get("id")
            msg_record.gmail_thread_id = result.get("threadId")
            msg_record.sent_at = datetime.now(timezone.utc)
            msg_record.error_message = None

            # Update settings counters
            aut_settings.emails_sent_today += 1
            aut_settings.last_sent_at = msg_record.sent_at

            db.commit()
            db.refresh(msg_record)
            return msg_record

        except (httpx.TimeoutException, GmailTimeoutError) as timeout_exc:
            # Ambiguous timeout: request may have reached Gmail before connection dropped.
            # Do NOT blindly retry; record OUTCOME_UNKNOWN.
            logger.error(f"Gmail send request timed out for message {msg_record.id}: {str(timeout_exc)}")
            msg_record.status = EmailMessageStatus.OUTCOME_UNKNOWN
            msg_record.error_message = "Request timed out during Gmail API call. Outcome unknown; do not retry blindly."
            db.commit()
            db.refresh(msg_record)
            raise GmailSendError(msg_record.error_message) from timeout_exc

        except Exception as exc:
            logger.error(f"Failed to send email via Gmail: {str(exc)}", exc_info=True)
            msg_record.status = EmailMessageStatus.FAILED
            msg_record.error_message = str(exc)
            db.commit()
            db.refresh(msg_record)
            raise GmailSendError(f"Failed to send email: {str(exc)}") from exc

    # --- 5. Targeted Reply Monitoring ---

    @classmethod
    def sync_replies_for_user(cls, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Polls only threads associated with messages sent through OutReachIQ.
        Extracts incoming replies, records them, and suppresses automated follow-up sequences.
        """
        conn = db.query(GmailConnection).filter(GmailConnection.user_id == user_id, GmailConnection.is_active == True).first()
        if not conn:
            return {"synced_threads_count": 0, "new_replies_count": 0, "status": "DISCONNECTED", "last_synced_at": datetime.now(timezone.utc)}

        # Find sent messages that have a valid thread_id
        sent_messages = (
            db.query(OutreachEmailMessage)
            .filter(
                OutreachEmailMessage.user_id == user_id,
                OutreachEmailMessage.status == EmailMessageStatus.SENT,
                OutreachEmailMessage.gmail_thread_id.isnot(None)
            )
            .all()
        )

        if not sent_messages:
            conn.last_synced_at = datetime.now(timezone.utc)
            db.commit()
            return {"synced_threads_count": 0, "new_replies_count": 0, "status": "COMPLETED", "last_synced_at": conn.last_synced_at}

        try:
            access_token, _ = cls.get_valid_access_token(db, user_id)
        except Exception as e:
            logger.error(f"Failed to obtain access token for reply monitoring: {str(e)}")
            return {"synced_threads_count": 0, "new_replies_count": 0, "status": "AUTH_ERROR", "last_synced_at": datetime.now(timezone.utc)}

        # Deduplicate thread IDs to query
        threads_map: Dict[str, List[OutreachEmailMessage]] = {}
        for msg in sent_messages:
            threads_map.setdefault(msg.gmail_thread_id, []).append(msg)

        new_replies_count = 0
        now_utc = datetime.now(timezone.utc)

        for thread_id, msgs in threads_map.items():
            try:
                if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET or settings.ENVIRONMENT == "test":
                    thread_data = MockGmailClient.get_thread(access_token, thread_id)
                else:
                    with httpx.Client(timeout=15.0) as http_client:
                        res = http_client.get(
                            f"{cls.GMAIL_THREADS_URL}/{thread_id}",
                            headers={"Authorization": f"Bearer {access_token}"},
                            params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]}
                        )
                        if res.status_code != 200:
                            logger.warning(f"Failed to fetch thread {thread_id}: {res.status_code}")
                            continue
                        thread_data = res.json()

                raw_msgs = thread_data.get("messages", [])
                for rm in raw_msgs:
                    rm_id = rm.get("id")
                    if not rm_id:
                        continue

                    # Check if reply already recorded
                    existing_reply = db.query(OutreachEmailReply).filter(OutreachEmailReply.gmail_message_id == rm_id).first()
                    if existing_reply:
                        continue

                    # Extract headers
                    headers = {h.get("name", "").lower(): h.get("value", "") for h in rm.get("payload", {}).get("headers", [])}
                    from_header = headers.get("from", "")

                    # Check if sender is not our own connected address (i.e. incoming from recipient)
                    if conn.email_address.lower() not in from_header.lower():
                        # Parse sender address
                        from_email = from_header
                        from_name = None
                        if "<" in from_header and ">" in from_header:
                            from_name = from_header.split("<")[0].strip().strip('"')
                            from_email = from_header.split("<")[1].split(">")[0].strip()

                        subject_hdr = headers.get("subject", "Re: Outreach")
                        snippet = rm.get("snippet", "")
                        internal_date_ms = rm.get("internalDate")
                        if internal_date_ms:
                            received_at = datetime.fromtimestamp(int(internal_date_ms) / 1000.0, tz=timezone.utc)
                        else:
                            received_at = now_utc

                        # Associate reply with parent message
                        parent_msg = msgs[0]

                        new_reply = OutreachEmailReply(
                            user_id=user_id,
                            message_id=parent_msg.id,
                            gmail_message_id=rm_id,
                            gmail_thread_id=thread_id,
                            from_email=from_email,
                            from_name=from_name,
                            subject=subject_hdr,
                            snippet=snippet,
                            received_at=received_at
                        )
                        db.add(new_reply)

                        # Update parent message
                        parent_msg.has_reply = True
                        parent_msg.reply_count += 1
                        parent_msg.last_reply_at = received_at

                        new_replies_count += 1

            except Exception as e:
                logger.error(f"Error checking replies for thread {thread_id}: {str(e)}")

        conn.last_synced_at = now_utc
        db.commit()

        return {
            "synced_threads_count": len(threads_map),
            "new_replies_count": new_replies_count,
            "status": "COMPLETED",
            "last_synced_at": now_utc
        }
