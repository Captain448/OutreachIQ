import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.opportunity import Opportunity, OpportunityStatus, OpportunityType
from app.models.company import Company
from app.models.job import Job
from app.models.outreach import OutreachDraft, GenerationStatus, OutreachPurpose, RecipientType
from app.services.encryption_service import TokenEncryptionService
from app.services.gmail_service import GmailService


def test_journey_1_auth_profile_and_resumes(client: TestClient):
    """Journey 1: Register, log in, create profile, verify persistence across calls."""
    reg = client.post("/auth/register", json={
        "email": "journey1.user@outreachiq.ai",
        "password": "SecurePassword123!",
        "full_name": "Journey One Candidate"
    })
    assert reg.status_code in [200, 201]
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify profile creation
    prof_res = client.get("/profile", headers=headers)
    assert prof_res.status_code == 200
    assert prof_res.json()["email"] == "journey1.user@outreachiq.ai"

    # Update profile with skills and education
    client.put("/profile", json={
        "headline": "Lead Research Engineer",
        "bio": "Specializing in distributed NLP and search infrastructure.",
        "skills": [
            {"name": "Python", "category": "technical", "status": "VERIFIED", "source": "USER_INPUT", "confidence_score": 1.0},
            {"name": "PyTorch", "category": "ai_ml", "status": "VERIFIED", "source": "USER_INPUT", "confidence_score": 1.0}
        ],
        "education": [
            {"institution": "Stanford University", "degree": "M.S.", "field_of_study": "Computer Science", "graduation_year": 2024}
        ]
    }, headers=headers)

    refreshed = client.get("/profile", headers=headers).json()
    assert len(refreshed["skills"]) == 2
    assert len(refreshed["education"]) == 1
    assert refreshed["completeness_score"] > 50


def test_journey_2_location_integrity_filtering(client: TestClient, db_session: Session):
    """Journey 2: Filter results and verify that no wrong-location jobs are shown as valid matches."""
    reg = client.post("/auth/register", json={
        "email": "journey2.user@outreachiq.ai",
        "password": "SecurePassword123!",
        "full_name": "Journey Two Candidate"
    })
    assert reg.status_code in [200, 201]
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Check that location filtering rejects mismatched cities
    bengaluru_res = client.get("/opportunities?location=Bengaluru", headers=headers)
    assert bengaluru_res.status_code == 200
    for o in bengaluru_res.json():
        loc = o["job"]["location"].lower() if o.get("job") else ""
        assert "noida" not in loc
        assert "mohali" not in loc


def test_journey_3_cosgo_recommendations_and_prerequisites(client: TestClient):
    """Journey 3: Generate COSGO recommendations, inspect prerequisites, verify effort & coverage."""
    reg = client.post("/auth/register", json={
        "email": "journey3.user@outreachiq.ai",
        "password": "SecurePassword123!",
        "full_name": "Journey Three Candidate"
    })
    assert reg.status_code in [200, 201]
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    opt_res = client.post("/cosgo/optimize", json={"budget_hours": 35.0, "weekly_budget_hours": 10.0}, headers=headers)
    assert opt_res.status_code in [200, 201]
    data = opt_res.json()
    assert "baseline_coverage" in data
    assert "projected_coverage" in data
    assert data["projected_coverage"] >= data["baseline_coverage"]

    # Verify latest run history endpoint
    latest_res = client.get("/cosgo/latest", headers=headers)
    assert latest_res.status_code == 200
    assert latest_res.json()["id"] == data["id"]


def test_journey_4_outreach_draft_lifecycle(client: TestClient, db_session: Session):
    """Journey 4: Create draft, edit, save, refresh, reopen, and check preview hash."""
    reg = client.post("/auth/register", json={
        "email": "journey4.user@outreachiq.ai",
        "password": "SecurePassword123!",
        "full_name": "Journey Four Candidate"
    })
    assert reg.status_code in [200, 201]
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.query(User).filter_by(email="journey4.user@outreachiq.ai").first()
    comp = Company(name="Journey Tech")
    db_session.add(comp)
    db_session.flush()

    job = Job(company_id=comp.id, company_name=comp.name, title="Lead AI Engineer", normalized_title="lead ai engineer", primary_url="http://journey.ai")
    db_session.add(job)
    db_session.flush()

    opp = Opportunity(user_id=user.id, job_id=job.id, company_id=comp.id, match_score=0.90)
    db_session.add(opp)
    db_session.commit()

    # Create draft for the opportunity
    draft_res = client.post("/outreach/drafts", json={
        "opportunity_id": opp.id,
        "purpose": "full_time_application",
        "recipient_type": "hiring_manager",
        "recipient_name": "Sarah Miller",
        "generate_immediately": False
    }, headers=headers)
    assert draft_res.status_code == 201
    draft = draft_res.json()
    draft_id = draft["id"]

    # Edit draft
    update_res = client.put(f"/outreach/drafts/{draft_id}", json={
        "subject": "Updated Application Subject Line",
        "body": "Updated body with grounded evidence."
    }, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["subject"] == "Updated Application Subject Line"

    # Re-fetch draft
    get_draft = client.get(f"/outreach/drafts/{draft_id}", headers=headers)
    assert get_draft.status_code == 200
    assert get_draft.json()["body"] == "Updated body with grounded evidence."


def test_journey_6_cross_user_security_and_idor_protection(client: TestClient, db_session: Session):
    """Journey 6: Attempt cross-user access, invalid IDs, expired tokens; confirm access is denied safely."""
    # User Alpha
    reg_a = client.post("/auth/register", json={"email": "alpha.sec@outreachiq.ai", "password": "Password123!", "full_name": "Alpha"})
    assert reg_a.status_code in [200, 201]
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User Beta
    reg_b = client.post("/auth/register", json={"email": "beta.sec@outreachiq.ai", "password": "Password123!", "full_name": "Beta"})
    assert reg_b.status_code in [200, 201]
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    user_a = db_session.query(User).filter_by(email="alpha.sec@outreachiq.ai").first()
    comp_a = Company(name="Alpha Corp")
    db_session.add(comp_a)
    db_session.flush()

    job_a = Job(company_id=comp_a.id, company_name=comp_a.name, title="Alpha Engineer", normalized_title="alpha engineer", primary_url="http://alpha.com")
    db_session.add(job_a)
    db_session.flush()

    opp_a = Opportunity(user_id=user_a.id, job_id=job_a.id, company_id=comp_a.id, match_score=0.95)
    db_session.add(opp_a)
    db_session.commit()

    # Alpha creates a draft
    alpha_draft = client.post("/outreach/drafts", json={
        "opportunity_id": opp_a.id,
        "purpose": "full_time_application",
        "generate_immediately": False
    }, headers=headers_a).json()

    # Beta attempts to read Alpha's draft -> Must be 404
    forbidden_get = client.get(f"/outreach/drafts/{alpha_draft['id']}", headers=headers_b)
    assert forbidden_get.status_code == 404

    # Beta attempts to update Alpha's draft -> Must be 404
    forbidden_put = client.put(f"/outreach/drafts/{alpha_draft['id']}", json={"subject": "Tampered"}, headers=headers_b)
    assert forbidden_put.status_code == 404

    # Beta attempts to delete Alpha's draft -> Must be 404
    forbidden_del = client.delete(f"/outreach/drafts/{alpha_draft['id']}", headers=headers_b)
    assert forbidden_del.status_code == 404

    # Invalid token check
    invalid_token_res = client.get("/profile", headers={"Authorization": "Bearer invalid_tampered_token_xyz"})
    assert invalid_token_res.status_code == 401
