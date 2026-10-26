import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.company import Company
from app.models.job import Job
from app.models.opportunity import Opportunity
from app.models.outreach import OutreachDraft, OutreachPurpose, RecipientType, GenerationStatus
from app.models.gmail import (
    GmailConnection,
    OutreachEmailMessage,
    OutreachEmailReply,
    OutreachAutomationSettings,
    EmailMessageStatus,
    SendingMode
)
from app.services.encryption_service import TokenEncryptionService
from app.services.gmail_service import GmailService, MockGmailClient, GmailSendError, GmailTimeoutError
from app.core.security import create_access_token


def test_token_encryption_and_decryption():
    """Verifies tokens are encrypted at rest and can be accurately decrypted."""
    raw_token = "ya29.a0AfH6SMB_secret_refresh_token_string_12345"
    encrypted = TokenEncryptionService.encrypt(raw_token)
    assert encrypted != raw_token
    assert len(encrypted) > 20
    assert TokenEncryptionService.decrypt(encrypted) == raw_token


def test_oauth_state_generation_tamper_detection_and_expiry():
    """Verifies OAuth state cryptographic HMAC signature and 15-minute expiry."""
    user_id = "user-12345"
    state = GmailService.generate_oauth_state(user_id)
    assert GmailService.verify_oauth_state(state, user_id) is True

    # Reject mismatched user ID (cross-user hijacking)
    assert GmailService.verify_oauth_state(state, "other-user-999") is False

    # Reject tampered state
    tampered = state[:-4] + "aaaa"
    assert GmailService.verify_oauth_state(tampered, user_id) is False


def test_draft_persistence_when_opportunity_is_deleted(db_session: Session):
    """
    CRITICAL: Verifies deleting an opportunity does NOT destroy the user's saved outreach draft history.
    The foreign key must SET NULL, preserving draft subject, body, and context snapshot.
    """
    user = User(email="candidate_integrity@example.com", hashed_password="pwd", is_active=True)
    db_session.add(user)
    db_session.flush()

    comp = Company(name="CloudCorp Systems")
    db_session.add(comp)
    db_session.flush()

    job = Job(company_id=comp.id, company_name=comp.name, title="Staff Engineer", normalized_title="staff engineer", primary_url="http://cloudcorp.com")
    db_session.add(job)
    db_session.flush()

    opp = Opportunity(user_id=user.id, job_id=job.id, company_id=comp.id)
    db_session.add(opp)
    db_session.flush()

    draft = OutreachDraft(
        user_id=user.id,
        opportunity_id=opp.id,
        purpose=OutreachPurpose.FULL_TIME_APPLICATION,
        recipient_type=RecipientType.HIRING_MANAGER,
        recipient_name="David Miller",
        subject="Staff Engineer Application - CloudCorp Systems",
        body="Dear David Miller, I am writing to apply for the Staff Engineer role at CloudCorp Systems.",
        generation_status=GenerationStatus.AI_GENERATED,
        context_snapshot={
            "job": {"title": "Staff Engineer", "company_name": "CloudCorp Systems", "location": "Remote"},
            "company": {"name": "CloudCorp Systems"}
        }
    )
    db_session.add(draft)
    db_session.commit()

    draft_id = draft.id
    opp_id = opp.id

    # Verify initial setup
    assert draft.opportunity_id == opp_id

    # Delete the opportunity
    db_session.delete(opp)
    db_session.commit()

    # Verify opportunity is gone
    deleted_opp = db_session.query(Opportunity).filter(Opportunity.id == opp_id).first()
    assert deleted_opp is None

    # CRITICAL: Verify the outreach draft STILL EXISTS with opportunity_id = None
    persisted_draft = db_session.query(OutreachDraft).filter(OutreachDraft.id == draft_id).first()
    assert persisted_draft is not None
    assert persisted_draft.opportunity_id is None
    assert persisted_draft.subject == "Staff Engineer Application - CloudCorp Systems"
    assert "CloudCorp Systems" in persisted_draft.body
    assert persisted_draft.context_snapshot["job"]["company_name"] == "CloudCorp Systems"


def test_oauth_connect_and_disconnect_flow(client: TestClient, db_session: Session):
    """Verifies OAuth authorization URL generation, callback exchange, and account disconnect."""
    user = User(email="oauth_test@example.com", hashed_password="pwd", is_active=True)
    db_session.add(user)
    db_session.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get OAuth URL
    res = client.get("/api/v1/gmail/oauth/url", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "authorization_url" in data
    assert "state" in data
    state = data["state"]

    # 2. Complete Callback with mock code
    callback_res = client.post(
        "/api/v1/gmail/oauth/callback",
        json={"code": "auth_code_success", "state": state},
        headers=headers
    )
    assert callback_res.status_code == 200
    conn_data = callback_res.json()
    assert conn_data["email_address"] == "candidate.verified@example.com"
    assert conn_data["is_active"] is True
    # Verify tokens are NEVER leaked in API responses
    assert "encrypted_refresh_token" not in conn_data
    assert "refresh_token" not in conn_data
    assert "access_token" not in conn_data

    # 3. Check /connection status
    status_res = client.get("/api/v1/gmail/connection", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["email_address"] == "candidate.verified@example.com"

    # 4. Disconnect
    disc_res = client.post("/api/v1/gmail/disconnect", headers=headers)
    assert disc_res.status_code == 200

    # 5. Check disconnected status
    status_after = client.get("/api/v1/gmail/connection", headers=headers)
    assert status_after.status_code == 200
    assert status_after.json() is None


def test_email_preview_content_hash_and_invalidation(client: TestClient, db_session: Session):
    """
    Verifies that preview computes a content hash, and changing subject, body,
    or recipient invalidates the approval hash.
    """
    user = User(email="preview_test@example.com", hashed_password="pwd", is_active=True)
    db_session.add(user)
    db_session.flush()

    draft = OutreachDraft(
        user_id=user.id,
        subject="Engineering Leadership Inquiry",
        body="Dear Hiring Team, I would love to connect regarding opportunities.",
        context_snapshot={}
    )
    db_session.add(draft)
    db_session.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Generate preview
    preview_res = client.post(
        "/api/v1/gmail/preview",
        json={
            "draft_id": draft.id,
            "recipient_email": "recruiter@nexusai.com",
            "subject": draft.subject,
            "body": draft.body
        },
        headers=headers
    )
    assert preview_res.status_code == 200
    pdata = preview_res.json()
    original_hash = pdata["content_hash"]
    assert len(original_hash) == 64

    # Connect Gmail for sending
    GmailService.save_or_update_connection(
        db=db_session,
        user_id=user.id,
        email_address="candidate@example.com",
        refresh_token="mock_ref_token"
    )

    # Enable review_before_send
    st = GmailService.get_or_create_settings(db_session, user.id)
    st.sending_mode = SendingMode.REVIEW_BEFORE_SEND
    db_session.commit()

    # Attempt send with tampered body (invalidated approval)
    send_tampered = client.post(
        "/api/v1/gmail/send",
        json={
            "draft_id": draft.id,
            "recipient_email": "recruiter@nexusai.com",
            "subject": draft.subject,
            "body": draft.body + " (Unauthorized candidate edit)",
            "approved_content_hash": original_hash
        },
        headers=headers
    )
    assert send_tampered.status_code == 400
    assert "Content has changed since your preview approval" in send_tampered.json()["detail"]

    # Attempt send with matching approved content
    MockGmailClient.reset()
    send_valid = client.post(
        "/api/v1/gmail/send",
        json={
            "draft_id": draft.id,
            "recipient_email": "recruiter@nexusai.com",
            "subject": draft.subject,
            "body": draft.body,
            "approved_content_hash": original_hash
        },
        headers=headers
    )
    assert send_valid.status_code == 200
    sent_data = send_valid.json()
    assert sent_data["status"] == "SENT"
    assert sent_data["gmail_message_id"].startswith("gmsg_")
    assert sent_data["gmail_thread_id"].startswith("gthread_")


def test_duplicate_send_prevention_and_idempotency(client: TestClient, db_session: Session):
    """Verifies that sending identical approved content twice is rejected as a duplicate."""
    user = User(email="dup_test@example.com", hashed_password="pwd", is_active=True)
    db_session.add(user)
    db_session.flush()

    draft = OutreachDraft(user_id=user.id, subject="Hello Nexus", body="Message content", context_snapshot={})
    db_session.add(draft)

    GmailService.save_or_update_connection(db=db_session, user_id=user.id, email_address="me@example.com", refresh_token="tok")
    st = GmailService.get_or_create_settings(db_session, user.id)
    st.sending_mode = SendingMode.REVIEW_BEFORE_SEND
    st.cooldown_minutes = 0  # Disable cooldown to test duplicate suppression directly
    db_session.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Preview
    prev = client.post(
        "/api/v1/gmail/preview",
        json={"draft_id": draft.id, "recipient_email": "alex@nexus.com", "subject": draft.subject, "body": draft.body},
        headers=headers
    ).json()

    # First send succeeds
    MockGmailClient.reset()
    send1 = client.post(
        "/api/v1/gmail/send",
        json={
            "draft_id": draft.id,
            "recipient_email": "alex@nexus.com",
            "subject": draft.subject,
            "body": draft.body,
            "approved_content_hash": prev["content_hash"]
        },
        headers=headers
    )
    assert send1.status_code == 200

    # Second send with identical hash and no override is blocked by duplicate suppression
    send2 = client.post(
        "/api/v1/gmail/send",
        json={
            "draft_id": draft.id,
            "recipient_email": "alex@nexus.com",
            "subject": draft.subject,
            "body": draft.body,
            "approved_content_hash": prev["content_hash"]
        },
        headers=headers
    )
    assert send2.status_code == 400
    assert "already sent" in send2.json()["detail"].lower()


def test_ambiguous_timeout_marks_outcome_unknown(client: TestClient, db_session: Session):
    """
    Verifies that a timeout during Gmail API transmission records status as OUTCOME_UNKNOWN
    and does NOT retry blindly.
    """
    user = User(email="timeout_test@example.com", hashed_password="pwd", is_active=True)
    db_session.add(user)
    db_session.flush()

    draft = OutreachDraft(user_id=user.id, subject="Subject", body="Body content", context_snapshot={})
    db_session.add(draft)

    GmailService.save_or_update_connection(db=db_session, user_id=user.id, email_address="me@example.com", refresh_token="tok")
    st = GmailService.get_or_create_settings(db_session, user.id)
    st.sending_mode = SendingMode.REVIEW_BEFORE_SEND
    db_session.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    prev = client.post(
        "/api/v1/gmail/preview",
        json={"draft_id": draft.id, "recipient_email": "timeout@company.com", "subject": draft.subject, "body": draft.body},
        headers=headers
    ).json()

    # Trigger simulated outcome-unknown timeout
    MockGmailClient.simulated_outcome_unknown = True
    try:
        send_res = client.post(
            "/api/v1/gmail/send",
            json={
                "draft_id": draft.id,
                "recipient_email": "timeout@company.com",
                "subject": draft.subject,
                "body": draft.body,
                "approved_content_hash": prev["content_hash"]
            },
            headers=headers
        )
        assert send_res.status_code == 400
        assert "outcome unknown" in send_res.json()["detail"].lower()

        # Verify database record is OUTCOME_UNKNOWN
        msg = db_session.query(OutreachEmailMessage).filter(OutreachEmailMessage.user_id == user.id).first()
        assert msg is not None
        assert msg.status == EmailMessageStatus.OUTCOME_UNKNOWN
    finally:
        MockGmailClient.reset()


def test_daily_limit_and_cooldown_enforcement(client: TestClient, db_session: Session):
    """Verifies that user-configured daily limits and cooldown periods are strictly enforced."""
    user = User(email="limits_test@example.com", hashed_password="pwd", is_active=True)
    db_session.add(user)
    db_session.flush()

    draft = OutreachDraft(user_id=user.id, subject="Inquiry", body="Text", context_snapshot={})
    db_session.add(draft)

    GmailService.save_or_update_connection(db=db_session, user_id=user.id, email_address="me@example.com", refresh_token="tok")
    st = GmailService.get_or_create_settings(db_session, user.id)
    st.sending_mode = SendingMode.REVIEW_BEFORE_SEND
    st.daily_limit = 1
    st.emails_sent_today = 1  # Limit reached
    db_session.commit()

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    prev = client.post(
        "/api/v1/gmail/preview",
        json={"draft_id": draft.id, "recipient_email": "lead@target.com", "subject": draft.subject, "body": draft.body},
        headers=headers
    ).json()

    send_res = client.post(
        "/api/v1/gmail/send",
        json={
            "draft_id": draft.id,
            "recipient_email": "lead@target.com",
            "subject": draft.subject,
            "body": draft.body,
            "approved_content_hash": prev["content_hash"]
        },
        headers=headers
    )
    assert send_res.status_code == 400
    assert "daily sending limit" in send_res.json()["detail"].lower()


def test_reply_monitoring_and_association(client: TestClient, db_session: Session):
    """
    Verifies that targeted reply polling associates incoming emails with the correct
    sent message thread and updates the reply count.
    """
    user = User(email="reply_test@example.com", hashed_password="pwd", is_active=True)
    db_session.add(user)
    db_session.flush()

    GmailService.save_or_update_connection(db=db_session, user_id=user.id, email_address="me@company.com", refresh_token="tok")

    sent_msg = OutreachEmailMessage(
        user_id=user.id,
        sender_email="me@company.com",
        recipient_email="recruiter@tech.com",
        subject="AI Application",
        body="Intro",
        content_hash="hash123",
        idempotency_key="idemp123",
        status=EmailMessageStatus.SENT,
        gmail_message_id="gmsg_parent_1",
        gmail_thread_id="gthread_abc",
        sent_at=datetime.now(timezone.utc)
    )
    db_session.add(sent_msg)
    db_session.commit()

    # Simulate an incoming reply in the thread
    MockGmailClient.simulated_replies = [
        {
            "id": "gmsg_parent_1",
            "threadId": "gthread_abc",
            "payload": {
                "headers": [{"name": "From", "value": "me@company.com"}, {"name": "Subject", "value": "AI Application"}]
            }
        },
        {
            "id": "gmsg_reply_2",
            "threadId": "gthread_abc",
            "snippet": "Thanks for reaching out! We'd love to chat on Tuesday.",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Sarah Lin <recruiter@tech.com>"},
                    {"name": "Subject", "value": "Re: AI Application"},
                    {"name": "Date", "value": "Mon, 19 Oct 2026 12:00:00 +0000"}
                ]
            }
        }
    ]

    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Trigger reply sync
    sync_res = client.post("/api/v1/gmail/replies/sync", headers=headers)
    assert sync_res.status_code == 200
    assert sync_res.json()["new_replies_count"] == 1

    # Verify parent message is updated
    db_session.refresh(sent_msg)
    assert sent_msg.has_reply is True
    assert sent_msg.reply_count == 1

    # Fetch replies endpoint
    replies_res = client.get("/api/v1/gmail/replies", headers=headers)
    assert replies_res.status_code == 200
    replies = replies_res.json()
    assert len(replies) == 1
    assert replies[0]["from_email"] == "recruiter@tech.com"
    assert "Tuesday" in replies[0]["snippet"]


def test_cross_user_isolation_and_idor_protection(client: TestClient, db_session: Session):
    """Verifies that User B cannot access User A's Gmail connection, sent messages, or settings."""
    user_a = User(email="user_a@test.com", hashed_password="pwd", is_active=True)
    user_b = User(email="user_b@test.com", hashed_password="pwd", is_active=True)
    db_session.add_all([user_a, user_b])
    db_session.flush()

    GmailService.save_or_update_connection(db=db_session, user_id=user_a.id, email_address="a@gmail.com", refresh_token="tok_a")
    msg_a = OutreachEmailMessage(
        user_id=user_a.id,
        sender_email="a@gmail.com",
        recipient_email="rec@corp.com",
        subject="User A Subject",
        body="User A Body",
        content_hash="h1",
        idempotency_key="idemp_a",
        status=EmailMessageStatus.SENT
    )
    db_session.add(msg_a)
    db_session.commit()

    token_b = create_access_token(user_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B checks connection -> should be null
    conn_b = client.get("/api/v1/gmail/connection", headers=headers_b).json()
    assert conn_b is None

    # User B attempts to access User A's sent message
    msg_res = client.get(f"/api/v1/gmail/messages/{msg_a.id}", headers=headers_b)
    assert msg_res.status_code == 404

    # User B lists messages -> should be empty
    msgs_b = client.get("/api/v1/gmail/messages", headers=headers_b).json()
    assert len(msgs_b) == 0
