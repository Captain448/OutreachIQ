import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.profile import Profile, Skill, SkillStatus, SkillSource, Project, WorkExperience, Education
from app.models.job import Job
from app.models.company import Company
from app.models.opportunity import Opportunity, OpportunityType, OpportunityStatus, RecommendedAction
from app.models.resume import Resume, ParsingStatus
from app.models.outreach import OutreachDraft, OutreachPurpose, RecipientType, GenerationStatus
from app.core.security import create_access_token
from app.services.outreach_context_builder import OutreachContextBuilder
from app.services.outreach_service import OutreachService


# ---------------------------------------------------------------------------
# Fixtures for Outreach Testing
# ---------------------------------------------------------------------------

@pytest.fixture
def outreach_users_and_data(db_session: Session):
    """Creates two distinct users with profiles, opportunities, and resumes for isolation testing."""
    # User 1
    u1 = User(
        email="alex.chen@example.com",
        hashed_password="hashed_pwd_123",
        full_name="Alex Chen",
        is_active=True
    )
    db_session.add(u1)
    db_session.flush()

    prof1 = Profile(
        user_id=u1.id,
        headline="Full Stack & AI Engineer",
        phone="+1-555-0199",
        location="San Francisco, CA",
        bio="Passionate engineer building distributed systems and machine learning workflows."
    )
    db_session.add(prof1)
    db_session.flush()

    # Skills for User 1
    s1 = Skill(profile_id=prof1.id, name="Python", status=SkillStatus.VERIFIED, source=SkillSource.USER_INPUT)
    s2 = Skill(profile_id=prof1.id, name="FastAPI", status=SkillStatus.VERIFIED, source=SkillSource.USER_INPUT)
    s3 = Skill(profile_id=prof1.id, name="Docker", status=SkillStatus.INFERRED, source=SkillSource.EXPERIENCE_INFERRED)
    db_session.add_all([s1, s2, s3])

    # Project for User 1
    p1 = Project(
        profile_id=prof1.id,
        title="Distributed Data Pipeline",
        description="Engineered an asynchronous ingestion pipeline processing 10k events/sec.",
        technologies=["Python", "FastAPI", "Docker", "PostgreSQL"],
        github_url="https://github.com/alexchen/datapipeline"
    )
    db_session.add(p1)

    # Opportunity 1 for User 1
    comp1 = Company(name="NexusAI Corp", classification="Startup")
    db_session.add(comp1)
    db_session.flush()

    job1 = Job(
        company_id=comp1.id,
        company_name=comp1.name,
        title="Backend Software Engineer",
        normalized_title="Software Engineer",
        location="San Francisco, CA",
        is_verified=True,
        verification_status="LISTING_FOUND_STATUS_VERIFIED_OPEN",
        description="Looking for an engineer experienced in Python and FastAPI to build high-throughput APIs.",
        primary_url="https://nexusai.example.com/jobs/123",
        application_url="https://nexusai.example.com/apply/123"
    )
    db_session.add(job1)
    db_session.flush()

    opp1 = Opportunity(
        user_id=u1.id,
        job_id=job1.id,
        company_id=comp1.id,
        match_score=0.88,
        matched_skills=["Python", "FastAPI"],
        missing_skills=["PostgreSQL"],
        status=OpportunityStatus.ACTIVE,
        recommended_action=RecommendedAction.CONTACT_NOW
    )
    db_session.add(opp1)

    # Resume for User 1
    res1 = Resume(
        user_id=u1.id,
        title="Backend Resume",
        target_role="Backend Engineer",
        filename="alex_backend.pdf",
        original_filename="alex_backend.pdf",
        file_path="/tmp/alex_backend.pdf",
        file_size=1024,
        mime_type="application/pdf",
        parsing_status=ParsingStatus.PARSED,
        extracted_skills=["Python", "FastAPI"]
    )
    db_session.add(res1)

    # User 2 (for isolation testing)
    u2 = User(
        email="beatrice.smith@example.com",
        hashed_password="hashed_pwd_456",
        full_name="Beatrice Smith",
        is_active=True
    )
    db_session.add(u2)
    db_session.flush()

    prof2 = Profile(user_id=u2.id, headline="Frontend Specialist")
    db_session.add(prof2)

    opp2 = Opportunity(
        user_id=u2.id,
        match_score=0.75,
        status=OpportunityStatus.ACTIVE,
        recommended_action=RecommendedAction.CONTACT_NOW
    )
    db_session.add(opp2)

    db_session.commit()

    return {
        "user1": u1,
        "token1": create_access_token(u1.id),
        "opp1": opp1,
        "job1": job1,
        "res1": res1,
        "user2": u2,
        "token2": create_access_token(u2.id),
        "opp2": opp2
    }


# ---------------------------------------------------------------------------
# Unit Tests for Context Builder & Grounding Rules
# ---------------------------------------------------------------------------

def test_outreach_context_builder_grounding(db_session: Session, outreach_users_and_data):
    """
    Verifies that OutreachContextBuilder strictly grounds candidate evidence:
    - Verified skills are distinguished from inferred skills
    - Inferred skills are NOT treated as verified
    - Matched portfolio projects are selected
    - Job verification status is captured accurately
    """
    data = outreach_users_and_data
    u1 = data["user1"]
    opp1 = data["opp1"]

    context = OutreachContextBuilder.build_context(
        db=db_session,
        user_id=u1.id,
        opportunity_id=opp1.id,
        recipient_name="Sarah Connor",
        recipient_role="VP of Engineering",
        purpose="full_time_application",
        recipient_type="hiring_manager"
    )

    candidate = context["candidate"]
    assert candidate["name"] == "Alex Chen"
    assert "Python" in candidate["verified_skills"]
    assert "FastAPI" in candidate["verified_skills"]
    # Docker was INFERRED in profile; must appear in inferred_skills, NOT verified_skills
    assert "Docker" in candidate["inferred_skills"]
    assert "Docker" not in candidate["verified_skills"]

    # Relevant project cited
    projects = candidate["relevant_projects"]
    assert len(projects) >= 1
    assert projects[0]["title"] == "Distributed Data Pipeline"

    # Job information
    job = context["job"]
    assert job["title"] == "Backend Software Engineer"
    assert job["company_name"] == "NexusAI Corp"
    assert job["is_verified_opening"] is True
    assert job["is_uncertain_or_closed"] is False

    # Parameters
    params = context["outreach_parameters"]
    assert params["recipient_name"] == "Sarah Connor"
    assert params["recipient_role"] == "VP of Engineering"


def test_outreach_service_mock_draft_generation(db_session: Session, outreach_users_and_data):
    """
    Tests mock generation generates a professional, truth-grounded draft with candidate and company facts,
    and without hallucinating unknown contact names when omitted.
    """
    data = outreach_users_and_data
    u1 = data["user1"]
    opp1 = data["opp1"]

    # Case A: Recipient name provided
    ctx_with_name = OutreachContextBuilder.build_context(
        db=db_session,
        user_id=u1.id,
        opportunity_id=opp1.id,
        recipient_name="Jane Doe",
        purpose="full_time_application"
    )
    draft_a = OutreachService.generate_draft_content(ctx_with_name)
    assert "Hi Jane Doe," in draft_a["body"]
    assert "NexusAI Corp" in draft_a["body"]
    assert "Backend Software Engineer" in draft_a["subject"]
    assert "Alex Chen" in draft_a["body"]
    assert draft_a["status"] == GenerationStatus.AI_GENERATED

    # Case B: Recipient name omitted -> must NOT hallucinate a person name!
    ctx_no_name = OutreachContextBuilder.build_context(
        db=db_session,
        user_id=u1.id,
        opportunity_id=opp1.id,
        recipient_name=None,
        purpose="full_time_application"
    )
    draft_b = OutreachService.generate_draft_content(ctx_no_name)
    assert "Hello NexusAI Corp Team," in draft_b["body"]
    assert "Hi None" not in draft_b["body"]


def test_manual_starter_draft_creation(db_session: Session, outreach_users_and_data):
    """Verifies manual starter draft creates a structured starter template with status DRAFT."""
    data = outreach_users_and_data
    u1 = data["user1"]
    opp1 = data["opp1"]

    ctx = OutreachContextBuilder.build_context(db=db_session, user_id=u1.id, opportunity_id=opp1.id)
    manual_draft = OutreachService.create_manual_starter_draft(ctx)

    assert manual_draft["status"] == GenerationStatus.DRAFT
    assert "Inquiry regarding Backend Software Engineer" in manual_draft["subject"]
    assert "Alex Chen" in manual_draft["body"]


# ---------------------------------------------------------------------------
# API Endpoint Integration Tests & Authorization Isolation
# ---------------------------------------------------------------------------

def test_outreach_draft_lifecycle_and_crud(db_session: Session, outreach_users_and_data, client: TestClient):
    """
    Tests the complete CRUD lifecycle for outreach drafts:
    1. Create draft from opportunity
    2. Get draft
    3. Update draft (user edits)
    4. Regenerate draft (verifies previous edits archived in snapshot)
    5. List drafts
    6. Delete draft
    """
    data = outreach_users_and_data
    token = data["token1"]
    opp1 = data["opp1"]
    res1 = data["res1"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create draft
    create_payload = {
        "opportunity_id": opp1.id,
        "resume_id": res1.id,
        "purpose": "full_time_application",
        "recipient_type": "hiring_manager",
        "recipient_name": "Marcus Aurelius",
        "recipient_role": "Engineering Director",
        "generate_immediately": True
    }
    resp = client.post("/api/v1/outreach/drafts", json=create_payload, headers=headers)
    assert resp.status_code == 201
    draft_data = resp.json()
    draft_id = draft_data["id"]
    assert draft_data["opportunity_id"] == opp1.id
    assert draft_data["recipient_name"] == "Marcus Aurelius"
    assert "Backend Software Engineer" in draft_data["subject"]
    assert draft_data["is_user_edited"] is False

    # 2. Get single draft
    get_resp = client.get(f"/api/v1/outreach/drafts/{draft_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == draft_id
    assert get_resp.json()["company_name"] == "NexusAI Corp"

    # 3. Update draft (User edits)
    custom_subject = "Refined: Inquiry regarding Backend Role"
    custom_body = "Customized body text by candidate with specific portfolio highlights."
    update_payload = {
        "subject": custom_subject,
        "body": custom_body,
        "user_notes": "Follow up next Tuesday if no response"
    }
    put_resp = client.put(f"/api/v1/outreach/drafts/{draft_id}", json=update_payload, headers=headers)
    assert put_resp.status_code == 200
    updated_data = put_resp.json()
    assert updated_data["subject"] == custom_subject
    assert updated_data["body"] == custom_body
    assert updated_data["is_user_edited"] is True
    assert updated_data["generation_status"] == GenerationStatus.MANUALLY_EDITED

    # 4. Regenerate draft (Verifies previous user edit is archived in snapshot)
    regen_resp = client.post(
        f"/api/v1/outreach/drafts/{draft_id}/generate",
        json={"purpose": "recruiter_introduction"},
        headers=headers
    )
    assert regen_resp.status_code == 200
    regen_data = regen_resp.json()
    assert regen_data["purpose"] == "recruiter_introduction"
    # Previous user edit must be safely preserved in context_snapshot previous_revisions
    snapshot = regen_data["context_snapshot"]
    assert "previous_revisions" in snapshot
    assert len(snapshot["previous_revisions"]) >= 1
    assert snapshot["previous_revisions"][-1]["body"] == custom_body

    # 5. List drafts
    list_resp = client.get("/api/v1/outreach/drafts", headers=headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(d["id"] == draft_id for d in list_data["items"])

    # 6. Delete draft
    del_resp = client.delete(f"/api/v1/outreach/drafts/{draft_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Confirm deleted
    get_after_del = client.get(f"/api/v1/outreach/drafts/{draft_id}", headers=headers)
    assert get_after_del.status_code == 404


def test_cross_user_isolation_and_idor_protection(db_session: Session, outreach_users_and_data, client: TestClient):
    """
    Enforces strict security boundaries:
    - User 2 CANNOT read, update, regenerate, or delete User 1's draft (HTTP 404)
    - User 2 CANNOT create a draft referencing User 1's opportunity or resume (HTTP 404)
    """
    data = outreach_users_and_data
    token1 = data["token1"]
    token2 = data["token2"]
    opp1 = data["opp1"]
    res1 = data["res1"]

    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    # 1. User 1 creates a draft
    create_resp = client.post(
        "/api/v1/outreach/drafts",
        json={"opportunity_id": opp1.id, "generate_immediately": True},
        headers=headers1
    )
    assert create_resp.status_code == 201
    draft_id = create_resp.json()["id"]

    # 2. User 2 attempts to GET User 1's draft -> 404
    get_by_u2 = client.get(f"/api/v1/outreach/drafts/{draft_id}", headers=headers2)
    assert get_by_u2.status_code == 404

    # 3. User 2 attempts to UPDATE User 1's draft -> 404
    put_by_u2 = client.put(
        f"/api/v1/outreach/drafts/{draft_id}",
        json={"body": "Hacked body"},
        headers=headers2
    )
    assert put_by_u2.status_code == 404

    # 4. User 2 attempts to REGENERATE User 1's draft -> 404
    regen_by_u2 = client.post(f"/api/v1/outreach/drafts/{draft_id}/generate", headers=headers2)
    assert regen_by_u2.status_code == 404

    # 5. User 2 attempts to DELETE User 1's draft -> 404
    del_by_u2 = client.delete(f"/api/v1/outreach/drafts/{draft_id}", headers=headers2)
    assert del_by_u2.status_code == 404

    # 6. IDOR Check: User 2 attempts to create a draft referencing User 1's opportunity -> 404
    idor_create = client.post(
        "/api/v1/outreach/drafts",
        json={"opportunity_id": opp1.id},
        headers=headers2
    )
    assert idor_create.status_code == 404

    # 7. IDOR Check: User 2 attempts to create a draft referencing User 1's resume -> 404
    idor_resume = client.post(
        "/api/v1/outreach/drafts",
        json={"opportunity_id": data["opp2"].id, "resume_id": res1.id},
        headers=headers2
    )
    assert idor_resume.status_code == 404


def test_eligible_opportunities_dropdown_endpoint(db_session: Session, outreach_users_and_data, client: TestClient):
    """Verifies that the /outreach/opportunities endpoint returns only the authenticated user's opportunities."""
    data = outreach_users_and_data
    token1 = data["token1"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    resp = client.get("/api/v1/outreach/opportunities", headers=headers1)
    assert resp.status_code == 200
    opps = resp.json()
    assert len(opps) == 1
    assert opps[0]["id"] == data["opp1"].id
    assert opps[0]["company_name"] == "NexusAI Corp"
    assert opps[0]["job_title"] == "Backend Software Engineer"


def test_outreach_uncertain_or_expired_opportunity(db_session: Session, outreach_users_and_data):
    """
    Verifies that when an opportunity has expired or unverified status:
    1. is_uncertain_or_closed is marked True in context
    2. The draft reflects status uncertainty as an exploratory inquiry
    """
    data = outreach_users_and_data
    u1 = data["user1"]
    job1 = data["job1"]
    job1.is_verified = False
    job1.verification_status = "LISTING_FOUND_STATUS_EXPIRED_OR_CLOSED"
    db_session.commit()

    context = OutreachContextBuilder.build_context(
        db=db_session,
        user_id=u1.id,
        opportunity_id=data["opp1"].id
    )
    assert context["job"]["is_uncertain_or_closed"] is True

    draft = OutreachService.generate_draft_content(context)
    assert "exploratory" in draft["body"].lower() or "proactively" in draft["body"].lower()


def test_outreach_sparse_candidate_info(db_session: Session):
    """Verifies candidate with minimal/sparse information generates cleanly without errors."""
    sparse_user = User(email="newuser@example.com", hashed_password="pwd", is_active=True)
    db_session.add(sparse_user)
    db_session.flush()

    comp = Company(name="Acme Tech")
    db_session.add(comp)
    db_session.flush()

    job = Job(company_id=comp.id, company_name=comp.name, title="Junior Developer", normalized_title="junior developer", primary_url="http://acme.com")
    db_session.add(job)
    db_session.flush()

    opp = Opportunity(user_id=sparse_user.id, job_id=job.id, company_id=comp.id)
    db_session.add(opp)
    db_session.commit()

    context = OutreachContextBuilder.build_context(
        db=db_session,
        user_id=sparse_user.id,
        opportunity_id=opp.id
    )
    assert context["candidate"]["name"] == "Newuser"
    assert context["candidate"]["verified_skills"] == []

    draft = OutreachService.generate_draft_content(context)
    assert "Junior Developer" in draft["subject"]
    assert "Acme Tech" in draft["body"]


def test_llm_malformed_json_fallback(db_session: Session, outreach_users_and_data):
    """Verifies fallback when LLM outputs plain text instead of strict JSON."""
    data = outreach_users_and_data
    context = OutreachContextBuilder.build_context(
        db=db_session,
        user_id=data["user1"].id,
        opportunity_id=data["opp1"].id
    )

    raw_output = "Subject: High Throughput Backend Roles\n\nDear NexusAI Team,\n\nI am writing to express my interest."
    structured = OutreachService._fallback_structure(context, raw_output)
    assert structured["subject"] == "High Throughput Backend Roles"
    assert "NexusAI Team" in structured["body"]
    assert structured["status"] == GenerationStatus.AI_GENERATED


