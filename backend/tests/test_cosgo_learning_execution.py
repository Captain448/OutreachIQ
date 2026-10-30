import pytest
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.core.security import create_access_token
from app.models.user import User
from app.models.profile import Profile, Preferences, Skill, SkillStatus, SkillSource
from app.models.cosgo import CosgoRun, CosgoAction, CosgoProgressState
from app.models.learning import UserLearningPlan
from app.services.learning.learning_plan_service import LearningPlanService


@pytest.fixture
def test_user_with_cosgo(db_session):
    user = User(
        email=f"cosgo_learn_user_{int(time.time() * 1000)}@outreachiq.ai",
        full_name="COSGO Learning Candidate",
        hashed_password="pw_test_dummy",
        is_active=True
    )
    db_session.add(user)
    db_session.flush()

    # Create profile
    profile = Profile(
        user_id=user.id,
        headline="Senior Python Engineer"
    )
    db_session.add(profile)
    db_session.flush()

    # Candidate knows Python and SQL
    s1 = Skill(profile_id=profile.id, name="Python", status=SkillStatus.VERIFIED, source=SkillSource.USER_INPUT)
    s2 = Skill(profile_id=profile.id, name="SQL", status=SkillStatus.VERIFIED, source=SkillSource.USER_INPUT)
    db_session.add_all([s1, s2])

    # Create persisted COSGO Run with 3 actions: Docker, FastAPI, PostgreSQL
    now = datetime.now(timezone.utc)
    run = CosgoRun(
        user_id=user.id,
        budget_hours=40.0,
        weekly_budget_hours=10.0,
        target_roles=["Backend Engineer", "Platform Engineer"],
        algorithm_version="cosgo-v1.1-verified",
        status="completed",
        total_opportunities_analyzed=10,
        eligible_opportunities_count=8,
        excluded_opportunities_count=2,
        baseline_coverage=0.25,
        projected_coverage=0.65,
        marginal_coverage_increase=0.40,
        diagnostics={},
        created_at=now,
        updated_at=now
    )
    db_session.add(run)
    db_session.flush()

    act1 = CosgoAction(
        run_id=run.id,
        user_id=user.id,
        skill_name="Docker",
        category="DevOps & Containers",
        priority_rank=1,
        estimated_hours=18.0,
        effort_uncertainty_range={"min_hours": 12, "max_hours": 24, "confidence": "high"},
        marginal_coverage_gain=0.25,
        cumulative_coverage=0.50,
        opportunities_count=6,
        target_opportunity_ids=["opp-1", "opp-2", "opp-3"],
        target_opportunities_summary=[
            {"id": "opp-1", "title": "Senior Backend Developer", "company_name": "Apex Cloud", "match_score": 0.85},
            {"id": "opp-2", "title": "DevOps Engineer", "company_name": "Scale Systems", "match_score": 0.78}
        ],
        prerequisites=["Linux CLI Basics"],
        why_recommended="Required in 6 target opportunities; maximizes weighted opportunity coverage by +25.0 pp.",
        progress_state=CosgoProgressState.RECOMMENDED,
        created_at=now,
        updated_at=now
    )

    act2 = CosgoAction(
        run_id=run.id,
        user_id=user.id,
        skill_name="FastAPI",
        category="Backend Framework",
        priority_rank=2,
        estimated_hours=14.0,
        effort_uncertainty_range={"min_hours": 10, "max_hours": 18, "confidence": "high"},
        marginal_coverage_gain=0.15,
        cumulative_coverage=0.65,
        opportunities_count=4,
        target_opportunity_ids=["opp-4", "opp-5"],
        target_opportunities_summary=[
            {"id": "opp-4", "title": "Python API Engineer", "company_name": "Modern Flow", "match_score": 0.82}
        ],
        prerequisites=["Python"],
        why_recommended="Standard high-speed async backend framework unlocking 4 target roles.",
        progress_state=CosgoProgressState.RECOMMENDED,
        created_at=now,
        updated_at=now
    )

    db_session.add_all([act1, act2])
    db_session.commit()

    return user, run, [act1, act2]


@pytest.mark.anyio
async def test_cosgo_empty_state_when_no_optimization_run(db_session, client):
    """
    Direct navigation or API call without a COSGO run must return is_cosgo_empty_state=True
    and not silently fall back to generic software engineering skills.
    """
    orig_close = db_session.close
    db_session.close = lambda: None
    try:
        user = User(
            email=f"empty_cosgo_{int(time.time() * 1000)}@outreachiq.ai",
            full_name="Empty COSGO User",
            hashed_password="pw_test_dummy",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user.id)
        res = client.get("/api/v1/learning/cosgo-plan", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["is_cosgo_empty_state"] is True
        assert "No active Skill Gap Optimization recommendations found" in data["empty_state_message"]
        assert len(data["recommended_skills"]) == 0
        assert data["selected_skill_name"] is None
        assert data["skill_plan"] is None
    finally:
        db_session.close = orig_close


@pytest.mark.anyio
async def test_cosgo_single_source_of_truth_and_default_top_skill(test_user_with_cosgo, db_session, client):
    """
    Verifies that when COSGO recommendations exist:
    - Recommended skills list exclusively contains COSGO-recommended skills.
    - Omission of ?skill= query defaults to the #1 priority skill.
    - Content is skill-specific.
    """
    user, run, actions = test_user_with_cosgo
    token = create_access_token(user.id)

    res = client.get("/api/v1/learning/cosgo-plan", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["is_cosgo_empty_state"] is False
    assert len(data["recommended_skills"]) == 2
    skill_names = [s["skill_name"] for s in data["recommended_skills"]]
    assert skill_names == ["Docker", "FastAPI"]

    # Priority #1 default
    assert data["selected_skill_name"] == "Docker"
    plan = data["skill_plan"]
    assert plan is not None
    assert plan["skill_name"] == "Docker"
    assert plan["priority_rank"] == 1
    assert plan["marginal_coverage_gain"] == 0.25
    assert plan["opportunities_count"] == 6
    assert len(plan["target_opportunities_summary"]) == 2

    # Roadmap has 4 stages
    assert len(plan["roadmap_stages"]) == 4
    stage_ids = [s["stage_id"] for s in plan["roadmap_stages"]]
    assert stage_ids == ["fundamentals", "intermediate", "practical", "advanced"]


@pytest.mark.anyio
async def test_cosgo_navigation_by_query_param(test_user_with_cosgo, db_session, client):
    """
    Verifies passing ?skill=FastAPI selects FastAPI and generates its specific learning plan.
    """
    user, run, actions = test_user_with_cosgo
    token = create_access_token(user.id)

    res = client.get("/api/v1/learning/cosgo-plan?skill=FastAPI", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["selected_skill_name"] == "FastAPI"
    plan = data["skill_plan"]
    assert plan["skill_name"] == "FastAPI"
    assert plan["priority_rank"] == 2
    assert plan["marginal_coverage_gain"] == 0.15
    assert plan["diagnostic_note"] is None


@pytest.mark.anyio
async def test_invalid_skill_query_param_graceful_fallback(test_user_with_cosgo, db_session, client):
    """
    Passing a skill that is not in the active COSGO run must gracefully fall back to priority #1
    and provide an informative diagnostic note.
    """
    user, run, actions = test_user_with_cosgo
    token = create_access_token(user.id)

    res = client.get("/api/v1/learning/cosgo-plan?skill=UnrelatedSkillXYZ", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["selected_skill_name"] == "Docker"
    plan = data["skill_plan"]
    assert plan["skill_name"] == "Docker"
    assert "UnrelatedSkillXYZ" in plan["diagnostic_note"]
    assert "Displaying top-priority skill 'Docker' instead" in plan["diagnostic_note"]


@pytest.mark.anyio
async def test_strict_resource_relevance(test_user_with_cosgo, db_session, client):
    """
    Ensures that for Docker, only Docker-relevant resources and projects are returned.
    """
    user, run, actions = test_user_with_cosgo
    token = create_access_token(user.id)

    res = client.get("/api/v1/learning/cosgo-plan?skill=Docker", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    plan = res.json()["skill_plan"]

    # Documentation must be Docker
    assert plan["resources"]["documentation"] is not None
    assert "docker" in plan["resources"]["documentation"]["url"].lower()

    # All returned courses must cover Docker
    for course in plan["resources"]["courses"]:
        assert "docker" in [s.lower() for s in course["covered_skills"]] or "docker" in course["title"].lower()

    # All returned projects must feature Docker
    for proj in plan["projects"]:
        assert "docker" in [s.lower() for s in proj["target_skills"]]


@pytest.mark.anyio
async def test_honest_learning_progress_tracking(test_user_with_cosgo, db_session, client):
    """
    Tests marking roadmap milestones, exercises, resources, and overall state completed.
    Verifies that progress syncs with CosgoAction.
    """
    user, run, actions = test_user_with_cosgo
    token = create_access_token(user.id)

    # 1. Toggle milestone 'fundamentals'
    payload = {
        "skill_name": "Docker",
        "toggle_milestone_id": "fundamentals",
        "toggle_exercise_id": "ex-docker-1",
        "toggle_resource_url": "https://docs.docker.com/",
        "progress_state": "IN_PROGRESS"
    }
    res = client.patch("/api/v1/learning/progress", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    p_data = res.json()
    assert p_data["progress_state"] == "IN_PROGRESS"
    assert "fundamentals" in p_data["progress"]["completed_milestones"]
    assert "ex-docker-1" in p_data["progress"]["completed_exercises"]
    assert "https://docs.docker.com/" in p_data["progress"]["completed_resources"]

    # 2. Reload plan and verify is_completed flags on items
    plan_res = client.get("/api/v1/learning/cosgo-plan?skill=Docker", headers={"Authorization": f"Bearer {token}"})
    assert plan_res.status_code == 200
    plan = plan_res.json()["skill_plan"]
    assert plan["progress_state"] == "IN_PROGRESS"

    # Stage 1 fundamentals is completed, stage 2 is not
    stage1 = next(s for s in plan["roadmap_stages"] if s["stage_id"] == "fundamentals")
    assert stage1["is_completed"] is True
    stage2 = next(s for s in plan["roadmap_stages"] if s["stage_id"] == "intermediate")
    assert stage2["is_completed"] is False

    # Doc is completed
    assert plan["resources"]["documentation"]["is_completed"] is True

    # Exercise 1 is completed
    ex1 = next(e for e in plan["resources"]["practical_exercises"] if e["id"] == "ex-docker-1")
    assert ex1["is_completed"] is True

    # 3. Mark COMPLETED
    comp_payload = {
        "skill_name": "Docker",
        "progress_state": "COMPLETED",
        "user_notes": "Completed Docker fundamentals and multi-stage container builds"
    }
    res_comp = client.patch("/api/v1/learning/progress", json=comp_payload, headers={"Authorization": f"Bearer {token}"})
    assert res_comp.status_code == 200
    assert res_comp.json()["progress_state"] == "COMPLETED"

    # 4. Verify CosgoAction was synchronized
    db_session.expire_all()
    act = db_session.query(CosgoAction).filter(CosgoAction.id == actions[0].id).first()
    assert act.progress_state == CosgoProgressState.COMPLETED
    assert act.completed_at is not None
    assert act.user_notes == "Completed Docker fundamentals and multi-stage container builds"
