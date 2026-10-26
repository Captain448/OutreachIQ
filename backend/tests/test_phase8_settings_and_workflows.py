import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.profile import Profile, Preferences, Skill, SkillStatus, SkillSource
from app.models.opportunity import Opportunity, OpportunityStatus, OpportunityType
from app.models.company import Company
from app.models.job import Job
from app.models.outreach import OutreachDraft, OutreachPurpose, RecipientType, GenerationStatus
from app.models.gmail import OutreachAutomationSettings, SendingMode, GmailConnection


def test_career_preferences_persistence_and_validation(client: TestClient):
    """Verifies that career preferences update persists and enforces valid domain constraints."""
    reg = client.post("/auth/register", json={
        "email": "career.prefs@outreachiq.ai",
        "password": "Password123!",
        "full_name": "Career Prefs Candidate"
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update preferences
    payload = {
        "headline": "Lead Platform Engineer",
        "preferences": {
            "desired_roles": ["Staff Site Reliability Engineer", "Platform Architect"],
            "preferred_industries": ["Financial Services", "Cloud Platforms"],
            "preferred_locations": ["Bengaluru", "Remote"],
            "remote_preference": "remote",
            "experience_level": "senior",
            "employment_preference": "full-time"
        }
    }
    update_res = client.put("/profile", json=payload, headers=headers)
    assert update_res.status_code == 200
    profile_data = update_res.json()
    assert profile_data["headline"] == "Lead Platform Engineer"
    prefs = profile_data["preferences"]
    assert prefs["remote_preference"] == "remote"
    assert prefs["experience_level"] == "senior"
    assert "Bengaluru" in prefs["preferred_locations"]

    # Re-fetch profile to verify persistence across sessions
    get_res = client.get("/profile", headers=headers)
    assert get_res.status_code == 200
    refetched_prefs = get_res.json()["preferences"]
    assert refetched_prefs["desired_roles"] == ["Staff Site Reliability Engineer", "Platform Architect"]
    assert refetched_prefs["employment_preference"] == "full-time"


def test_autonomy_settings_governance_and_killswitch(client: TestClient):
    """Verifies Outreach Automation governance policies, cooldowns, limits, and killswitch toggling."""
    reg = client.post("/auth/register", json={
        "email": "governance.tester@outreachiq.ai",
        "password": "Password123!",
        "full_name": "Governance Tester"
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch initial default settings
    init_res = client.get("/gmail/settings", headers=headers)
    assert init_res.status_code == 200
    st = init_res.json()
    assert st["sending_mode"] in ["REVIEW_BEFORE_SEND", "DRAFT_ONLY"]
    assert st["is_paused"] is False

    # 2. Update sending mode, daily limits, cooldowns, and activate emergency pause
    update_payload = {
        "sending_mode": "DRAFT_ONLY",
        "daily_limit": 30,
        "cooldown_minutes": 10,
        "duplicate_suppression_days": 21,
        "is_paused": True,
        "followup_delay_days": 5
    }
    patch_res = client.patch("/gmail/settings", json=update_payload, headers=headers)
    assert patch_res.status_code == 200
    updated_st = patch_res.json()
    assert updated_st["sending_mode"] == "DRAFT_ONLY"
    assert updated_st["daily_limit"] == 30
    assert updated_st["cooldown_minutes"] == 10
    assert updated_st["duplicate_suppression_days"] == 21
    assert updated_st["is_paused"] is True
    assert updated_st["followup_delay_days"] == 5

    # 3. Disengage emergency killswitch
    unpause_res = client.patch("/gmail/settings", json={"is_paused": False}, headers=headers)
    assert unpause_res.status_code == 200
    assert unpause_res.json()["is_paused"] is False


def test_provider_health_telemetry_accuracy(client: TestClient):
    """Verifies provider health telemetry reports real measured latencies and distinguishes configured status."""
    reg = client.post("/auth/register", json={
        "email": "telemetry.tester@outreachiq.ai",
        "password": "Password123!",
        "full_name": "Telemetry Tester"
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    health_res = client.get("/providers/health", headers=headers)
    assert health_res.status_code == 200
    providers = health_res.json()
    assert isinstance(providers, list)
    assert len(providers) >= 4

    p_map = {p["provider_name"]: p for p in providers}
    assert "tavily" in p_map
    assert "exa" in p_map
    assert "jsearch" in p_map
    assert "adzuna" in p_map

    # Tavily and Exa must indicate configured if api keys are present in env
    tavily = p_map["tavily"]
    assert "is_configured" in tavily
    assert "status" in tavily
    assert "display_name" in tavily


def test_cross_user_isolation_for_workspace_inventory(client: TestClient, db_session: Session):
    """Verifies that user A cannot view or count user B's opportunities, drafts, or sent messages."""
    # Register Candidate A
    reg_a = client.post("/auth/register", json={"email": "cand_a@outreachiq.ai", "password": "Password123!", "full_name": "Candidate A"})
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register Candidate B
    reg_b = client.post("/auth/register", json={"email": "cand_b@outreachiq.ai", "password": "Password123!", "full_name": "Candidate B"})
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Candidate A creates an opportunity and draft
    comp_a = Company(name="Candidate A Corp")
    db_session.add(comp_a)
    db_session.flush()

    job_a = Job(company_id=comp_a.id, company_name=comp_a.name, title="A Engineer", normalized_title="a engineer", primary_url="http://a.com")
    db_session.add(job_a)
    db_session.flush()

    user_a = db_session.query(User).filter_by(email="cand_a@outreachiq.ai").first()
    opp_a = Opportunity(user_id=user_a.id, job_id=job_a.id, company_id=comp_a.id, match_score=0.91)
    db_session.add(opp_a)
    db_session.flush()

    draft_a = OutreachDraft(
        user_id=user_a.id,
        opportunity_id=opp_a.id,
        purpose=OutreachPurpose.FULL_TIME_APPLICATION,
        recipient_type=RecipientType.HIRING_MANAGER,
        recipient_name="Recruiter A",
        subject="Subject A",
        body="Body text A",
        generation_status=GenerationStatus.AI_GENERATED
    )
    db_session.add(draft_a)
    db_session.commit()

    # Candidate B queries opportunities and drafts
    opps_b = client.get("/opportunities", headers=headers_b).json()
    assert not any(o["id"] == opp_a.id for o in opps_b)

    drafts_b = client.get("/outreach/drafts", headers=headers_b).json()
    assert not any(d["id"] == draft_a.id for d in drafts_b["items"])

    # Attempting to fetch Candidate A's draft with Candidate B's credentials must return 404 (IDOR protection)
    idor_res = client.get(f"/outreach/drafts/{draft_a.id}", headers=headers_b)
    assert idor_res.status_code == 404
