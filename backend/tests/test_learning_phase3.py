import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.models.resume import Resume, ParsingStatus
from app.models.profile import Profile, Preferences, Skill, Project, SkillStatus, SkillSource
from app.models.learning import UserLearningPlan
from app.services.providers.youtube_adapter import YouTubeAdapter, CURATED_SKILL_VIDEOS
from app.services.providers.base_provider import PersistentQuotaTracker
from app.services.learning.doc_catalog import DocCatalogService
from app.services.learning.course_catalog import CourseCatalogService, AccessType
from app.services.learning.certification_directory import CertificationDirectoryService
from app.services.learning.project_recommender import ProjectRecommenderService
from app.services.learning.learning_plan_service import LearningPlanService


# -----------------------------------------------------------------------------
# 1. YouTube Adapter Tests: Missing/Invalid Keys, Quotas, Caching, Graceful Fallbacks
# -----------------------------------------------------------------------------

def test_youtube_adapter_unconfigured_when_key_missing():
    adapter = YouTubeAdapter(api_key=None, persist_quota=False)
    assert adapter.is_configured() is False
    can_run, reason = adapter.can_query()
    assert can_run is False
    assert "missing credentials or is unconfigured" in reason


def test_youtube_adapter_unconfigured_when_key_empty():
    adapter = YouTubeAdapter(api_key="   ", persist_quota=False)
    assert adapter.is_configured() is False
    can_run, reason = adapter.can_query()
    assert can_run is False


@pytest.mark.anyio
async def test_youtube_adapter_falls_back_to_curated_when_unconfigured():
    adapter = YouTubeAdapter(api_key=None, persist_quota=False)
    videos = await adapter.search_videos(query="Python", limit=2, prefer_curated_fallback=True)
    assert len(videos) > 0
    assert videos[0]["is_curated"] is True
    assert "https://www.youtube.com/watch?v=" in videos[0]["video_url"]


@pytest.mark.anyio
async def test_youtube_adapter_daily_quota_exhaustion_trips_circuit_breaker():
    adapter = YouTubeAdapter(api_key="AIzaSyDummyValidLengthKeyForTest", persist_quota=False)
    adapter.daily_request_cap = 2
    adapter.daily_requests_used = 2

    can_run, reason = adapter.can_query()
    assert can_run is False
    assert adapter.circuit_status == "quota_exhausted"
    assert "reached daily free quota cap" in reason

    # Falls back gracefully to curated tutorials rather than failing with an exception
    videos = await adapter.search_videos(query="Docker", limit=1, prefer_curated_fallback=True)
    assert len(videos) > 0
    assert videos[0]["is_curated"] is True


@pytest.mark.anyio
async def test_youtube_adapter_cache_hit():
    adapter = YouTubeAdapter(api_key="AIzaSyDummyValidLengthKeyForTest", persist_quota=False)
    mock_items = [
        {
            "id": {"videoId": "test_vid_123"},
            "snippet": {
                "title": "FastAPI Testing Tutorial",
                "channelTitle": "Python Dev",
                "description": "FastAPI tutorial",
                "thumbnails": {"medium": {"url": "https://img.youtube.com/vi/test_vid_123/hqdefault.jpg"}},
                "publishedAt": "2026-01-01T00:00:00Z"
            }
        }
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"items": mock_items}

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)) as mock_get:
        # First call -> hits network
        res1 = await adapter.search_videos("FastAPI", limit=1)
        assert len(res1) == 1
        assert res1[0]["video_id"] == "test_vid_123"
        assert mock_get.call_count == 1

        # Second identical call -> served from in-memory cache
        res2 = await adapter.search_videos("FastAPI", limit=1)
        assert len(res2) == 1
        assert res2[0]["video_id"] == "test_vid_123"
        # Network call count remains 1 due to cache hit
        assert mock_get.call_count == 1


# -----------------------------------------------------------------------------
# 2. Official Documentation Catalog & Resolver Tests
# -----------------------------------------------------------------------------

def test_doc_catalog_resolves_known_skills():
    python_doc = DocCatalogService.resolve_documentation("Python")
    assert python_doc is not None
    assert python_doc.skill_name == "Python"
    assert "docs.python.org" in python_doc.url
    assert python_doc.is_official is True

    fastapi_doc = DocCatalogService.resolve_documentation("fastapi")
    assert fastapi_doc is not None
    assert fastapi_doc.skill_name == "FastAPI"
    assert "fastapi.tiangolo.com" in python_doc.official_domain or "fastapi.tiangolo.com" in fastapi_doc.url


def test_doc_catalog_resolves_aliases():
    # k8s -> Kubernetes
    k8s_doc = DocCatalogService.resolve_documentation("k8s")
    assert k8s_doc is not None
    assert k8s_doc.skill_name == "Kubernetes"
    assert "kubernetes.io" in k8s_doc.url

    # postgres -> PostgreSQL
    pg_doc = DocCatalogService.resolve_documentation("postgres")
    assert pg_doc is not None
    assert pg_doc.skill_name == "PostgreSQL"


def test_doc_catalog_unknown_skill_returns_none():
    unknown = DocCatalogService.resolve_documentation("NonExistentCustomFramework99")
    assert unknown is None


def test_doc_catalog_search():
    results = DocCatalogService.search_documentation("container")
    assert len(results) > 0
    names = [r.skill_name for r in results]
    assert "Docker" in names or "Kubernetes" in names


# -----------------------------------------------------------------------------
# 3. Course Discovery Catalog Tests (Pricing & Certification Transparency)
# -----------------------------------------------------------------------------

@pytest.mark.anyio
async def test_course_pricing_transparency():
    courses = CourseCatalogService.get_all_courses()
    assert len(courses) >= 8

    # FreeCodeCamp must be 100% Free with verified certificate
    fcc = next((c for c in courses if "freeCodeCamp" in c.provider_name), None)
    assert fcc is not None
    assert fcc.access_type == AccessType.FREE_COURSE
    assert fcc.certificate_included is True

    # Harvard CS50 must be Free to Audit without certificate
    cs50 = next((c for c in courses if "Harvard" in c.organization or "CS50" in c.title), None)
    assert cs50 is not None
    assert cs50.access_type == AccessType.FREE_TO_AUDIT
    assert cs50.certificate_included is False


@pytest.mark.anyio
async def test_course_search_filters_by_skill_and_access():
    py_courses = await CourseCatalogService.find_courses_for_skills(["Python"], limit_per_skill=5)
    assert len(py_courses) > 0
    for c in py_courses:
        assert any("python" in s.lower() for s in c.covered_skills) or "python" in c.title.lower()


# -----------------------------------------------------------------------------
# 4. Certification Directory Tests (Vendor Separation, Fee Verification)
# -----------------------------------------------------------------------------

def test_certification_directory_fees_and_urls():
    certs = CertificationDirectoryService.get_all_certifications()
    assert len(certs) >= 6

    # Verify AWS Solutions Architect
    aws_cert = next((c for c in certs if "AWS" in c.issuing_organization), None)
    assert aws_cert is not None
    assert aws_cert.exam_cost_status == "PAID"
    assert "aws.amazon.com" in aws_cert.official_url
    assert aws_cert.learning_material_free_status == "FREE"

    # Verify CKA
    cka = next((c for c in certs if "CKA" in c.id or "Kubernetes" in c.name), None)
    assert cka is not None
    assert cka.exam_cost_status == "PAID"
    assert "cncf.io" in cka.official_url


def test_certification_search_by_skill_and_role():
    matched = CertificationDirectoryService.find_certifications_for_skills_and_roles(
        skills=["Kubernetes", "Docker"],
        roles=["DevOps Engineer"],
        limit=3
    )
    assert len(matched) > 0
    cert_names = [c.name for c in matched]
    assert any("Kubernetes" in name or "AWS" in name for name in cert_names)


# -----------------------------------------------------------------------------
# 5. Project Recommender Tests (Profile Awareness, Deduplication, Structure)
# -----------------------------------------------------------------------------

def test_project_recommendations_structure():
    blueprints = ProjectRecommenderService.recommend_projects(
        candidate_skills=["Python", "SQL"],
        skill_gaps=["FastAPI", "Docker", "PostgreSQL"],
        target_roles=["Backend Developer"],
        limit=2
    )
    assert len(blueprints) > 0
    bp = blueprints[0]
    assert bp.is_estimate is True
    assert bp.estimated_hours > 0
    assert len(bp.milestones) >= 3
    assert len(bp.deliverables) >= 2
    assert len(bp.validation_checklist) >= 2
    assert len(bp.skill_gaps_addressed) > 0


def test_project_recommendations_deduplicates_existing_user_projects():
    # User already has built a "High-Throughput Asynchronous Task Processing Engine"
    existing = [
        {"title": "High-Throughput Asynchronous Task Processing Engine", "description": "Existing project"}
    ]
    blueprints = ProjectRecommenderService.recommend_projects(
        candidate_skills=["Python"],
        skill_gaps=["FastAPI", "Docker"],
        target_roles=["Backend Developer"],
        existing_projects=existing,
        limit=5
    )
    titles = [b.title for b in blueprints]
    assert "High-Throughput Asynchronous Task Processing Engine" not in titles


# -----------------------------------------------------------------------------
# 6. Learning Plan Service & Budget Tests (Sequencing, Onboarding State)
# -----------------------------------------------------------------------------

@pytest.mark.anyio
async def test_learning_plan_empty_candidate_returns_onboarding_state(db_session):
    orig_close = db_session.close
    db_session.close = lambda: None
    try:
        user = User(
            email=f"onboarding_user_{int(time.time())}@outreachiq.ai",
            full_name="New Onboarding User",
            hashed_password="pw_test_dummy",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        overview = await LearningPlanService.build_personalized_learning_overview(
            user_id=user.id,
            db=db_session,
            include_youtube=False
        )
        assert overview["is_onboarding_empty_state"] is True
        assert "Welcome to OutReachIQ Learning" in overview["message"]
        assert len(overview["recommended_skills"]) == 0
    finally:
        db_session.close = orig_close


@pytest.mark.anyio
async def test_learning_plan_time_budget_recalculates_timeline(db_session):
    orig_close = db_session.close
    db_session.close = lambda: None
    try:
        user = User(
            email=f"budget_user_{int(time.time())}@outreachiq.ai",
            full_name="Budget Candidate",
            hashed_password="pw_test_dummy",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        profile = Profile(user_id=user.id, headline="Aspiring Backend Engineer")
        db_session.add(profile)
        db_session.commit()

        pref = Preferences(
            profile_id=profile.id,
            desired_roles=["Backend Developer"],
            preferred_locations=["Remote"]
        )
        db_session.add(pref)
        db_session.commit()

        # 1. 10 hours/week budget
        LearningPlanService.update_weekly_budget(user.id, weekly_hours=10.0, db=db_session)
        plan10 = await LearningPlanService.build_personalized_learning_overview(user.id, db=db_session, include_youtube=False)
        assert plan10["weekly_hours_budget"] == 10.0
        weeks10 = plan10["total_estimated_weeks"]

        # 2. 20 hours/week budget
        LearningPlanService.update_weekly_budget(user.id, weekly_hours=20.0, db=db_session)
        plan20 = await LearningPlanService.build_personalized_learning_overview(user.id, db=db_session, include_youtube=False)
        assert plan20["weekly_hours_budget"] == 20.0
        weeks20 = plan20["total_estimated_weeks"]

        # 20 hours/week should take roughly half the weeks of 10 hours/week
        assert weeks20 <= weeks10
    finally:
        db_session.close = orig_close


# -----------------------------------------------------------------------------
# 7. Security & API Endpoint Tests (Authentication & IDOR Isolation)
# -----------------------------------------------------------------------------

def test_learning_endpoints_require_authentication(client):
    res1 = client.get("/api/v1/learning/overview")
    assert res1.status_code in (401, 403)

    res2 = client.put("/api/v1/learning/budget", json={"weekly_hours": 15.0})
    assert res2.status_code in (401, 403)


def test_public_learning_catalog_endpoints(client):
    # Documentation catalog is public and requires no auth
    res_docs = client.get("/api/v1/learning/docs?query=python")
    assert res_docs.status_code == 200
    docs = res_docs.json()
    assert len(docs) > 0
    assert docs[0]["skill_name"] == "Python"

    # Courses endpoint is public
    res_courses = client.get("/api/v1/learning/courses?skill=Python")
    assert res_courses.status_code == 200

    # Certifications endpoint is public
    res_certs = client.get("/api/v1/learning/certifications")
    assert res_certs.status_code == 200

    # Health endpoint is public and exposes no secrets
    res_health = client.get("/api/v1/learning/health")
    assert res_health.status_code == 200
    data = res_health.json()
    assert "youtube" in data
    assert "documentation_catalog" in data
    assert "api_key" not in str(data).lower()


# -----------------------------------------------------------------------------
# 8. Resume Model Integration & Regression Tests (AttributeError Fix Verification)
# -----------------------------------------------------------------------------

@pytest.mark.anyio
async def test_learning_overview_with_valid_parsed_resume(db_session, client):
    """
    Verifies that LearningPlanService safely reads from the actual SQLAlchemy Resume model
    fields (extracted_skills, extracted_projects, extracted_experience, parsed_text)
    without raising AttributeError: 'Resume' object has no attribute 'parsed_data'.
    """
    orig_close = db_session.close
    db_session.close = lambda: None
    try:
        user = User(
            email=f"valid_resume_user_{int(time.time() * 1000)}@outreachiq.ai",
            full_name="Valid Resume Candidate",
            hashed_password="pw_test_dummy",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        # Add an uploaded Resume with actual Resume model fields
        resume = Resume(
            user_id=user.id,
            title="Senior Backend Resume",
            target_role="Backend Developer",
            is_preferred=True,
            is_active=True,
            filename="backend_resume.pdf",
            original_filename="backend_resume.pdf",
            file_path="/uploads/backend_resume.pdf",
            file_size=20480,
            mime_type="application/pdf",
            parsed_text="Experienced Backend Developer skilled in Python, FastAPI, and PostgreSQL. Built High-Throughput Task Engine.",
            parsing_status=ParsingStatus.PARSED,
            parsing_confidence=0.95,
            extracted_skills=[
                {"name": "Python", "category": "programming_languages", "status": "VERIFIED"},
                {"name": "FastAPI", "category": "frameworks", "status": "VERIFIED"},
                {"name": "PostgreSQL", "category": "databases", "status": "VERIFIED"}
            ],
            extracted_projects=[
                {
                    "title": "High-Throughput Asynchronous Task Processing Engine",
                    "description": "Background worker queue with Redis and FastAPI",
                    "technologies": ["FastAPI", "Redis"]
                }
            ],
            extracted_experience=[
                {
                    "role": "Backend Engineer",
                    "company": "ScaleTech",
                    "raw_entry": "Backend Engineer at ScaleTech working on distributed systems",
                    "technologies": ["Python", "FastAPI"]
                }
            ],
            extracted_education=[
                {"raw_entry": "B.S. in Computer Science", "source": "resume_section"}
            ],
            raw_metadata={"page_count": 1}
        )
        db_session.add(resume)
        db_session.commit()

        # 1. Test service directly
        overview = await LearningPlanService.build_personalized_learning_overview(
            user_id=user.id,
            db=db_session,
            include_youtube=False
        )
        assert overview["is_onboarding_empty_state"] is False
        assert "Python" in overview["candidate_known_skills"]
        assert "FastAPI" in overview["candidate_known_skills"]
        assert "PostgreSQL" in overview["candidate_known_skills"]
        assert len(overview["candidate_experience"]) > 0
        assert overview["candidate_experience"][0]["role"] == "Backend Engineer"
        assert len(overview["learning_phases"]) > 0
        assert len(overview["recommended_projects"]) > 0

        # Existing project from resume should be deduplicated
        recommended_titles = [p["title"] for p in overview["recommended_projects"]]
        assert "High-Throughput Asynchronous Task Processing Engine" not in recommended_titles

        # 2. Test HTTP API endpoint with authenticated client
        token = create_access_token(user.id)
        res = client.get("/api/v1/learning/overview", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["is_onboarding_empty_state"] is False
        assert "Python" in data["candidate_known_skills"]
        assert len(data["learning_phases"]) > 0
    finally:
        db_session.close = orig_close


@pytest.mark.anyio
async def test_learning_overview_with_empty_parsed_resume(db_session, client):
    """
    Verifies that a resume with empty or None extracted fields (e.g. unparsed, failed OCR,
    empty parsed_text) is handled gracefully without errors.
    """
    orig_close = db_session.close
    db_session.close = lambda: None
    try:
        user = User(
            email=f"empty_resume_user_{int(time.time() * 1000)}@outreachiq.ai",
            full_name="Empty Resume Candidate",
            hashed_password="pw_test_dummy",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        # Resume with empty extracted lists and partial status
        resume = Resume(
            user_id=user.id,
            title="Empty Scan Resume",
            target_role="General",
            is_preferred=True,
            is_active=True,
            filename="empty_scan.pdf",
            original_filename="empty_scan.pdf",
            file_path="/uploads/empty_scan.pdf",
            file_size=1024,
            mime_type="application/pdf",
            parsed_text=None,
            parsing_status=ParsingStatus.PARTIAL,
            parsing_confidence=0.2,
            extracted_skills=[],
            extracted_projects=[],
            extracted_experience=[],
            extracted_education=[],
            raw_metadata={}
        )
        db_session.add(resume)
        db_session.commit()

        overview = await LearningPlanService.build_personalized_learning_overview(
            user_id=user.id,
            db=db_session,
            include_youtube=False
        )
        # Should gracefully fall back to standard software roles without blowing up
        assert overview["is_onboarding_empty_state"] is False
        assert len(overview["target_roles"]) > 0
        assert len(overview["learning_phases"]) > 0

        # Verify HTTP API returns 200
        token = create_access_token(user.id)
        res = client.get("/api/v1/learning/overview", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
    finally:
        db_session.close = orig_close


@pytest.mark.anyio
async def test_learning_overview_candidate_with_no_uploaded_resume(db_session, client):
    """
    Verifies that a candidate with no resumes uploaded returns the onboarding empty state.
    """
    orig_close = db_session.close
    db_session.close = lambda: None
    try:
        user = User(
            email=f"no_resume_user_{int(time.time() * 1000)}@outreachiq.ai",
            full_name="No Resume Candidate",
            hashed_password="pw_test_dummy",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user.id)
        res = client.get("/api/v1/learning/overview", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["is_onboarding_empty_state"] is True
        assert "Welcome to OutReachIQ Learning" in data["message"]
        assert len(data["recommended_skills"]) == 0
    finally:
        db_session.close = orig_close


@pytest.mark.anyio
async def test_learning_overview_multiple_uploaded_resumes(db_session, client):
    """
    Verifies that multiple resumes uploaded by a single candidate have their skills,
    projects, and experiences aggregated cleanly.
    """
    orig_close = db_session.close
    db_session.close = lambda: None
    try:
        user = User(
            email=f"multi_resume_user_{int(time.time() * 1000)}@outreachiq.ai",
            full_name="Multi Resume Candidate",
            hashed_password="pw_test_dummy",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        # Resume 1: Backend Developer
        r1 = Resume(
            user_id=user.id,
            title="Backend Resume",
            target_role="Backend Developer",
            is_preferred=True,
            is_active=True,
            filename="backend.pdf",
            original_filename="backend.pdf",
            file_path="/uploads/backend.pdf",
            file_size=15000,
            mime_type="application/pdf",
            parsed_text="Backend skills: Python, FastAPI",
            parsing_status=ParsingStatus.PARSED,
            parsing_confidence=0.9,
            extracted_skills=[{"name": "Python"}, {"name": "FastAPI"}],
            extracted_projects=[{"title": "FastAPI Async Gateway"}],
            extracted_experience=[{"role": "Backend Engineer", "company": "Alpha Corp"}],
            extracted_education=[]
        )
        # Resume 2: Cloud / DevOps
        r2 = Resume(
            user_id=user.id,
            title="Cloud DevOps Resume",
            target_role="DevOps Engineer",
            is_preferred=False,
            is_active=True,
            filename="devops.pdf",
            original_filename="devops.pdf",
            file_path="/uploads/devops.pdf",
            file_size=16000,
            mime_type="application/pdf",
            parsed_text="DevOps skills: Docker, Kubernetes, Linux",
            parsing_status=ParsingStatus.PARSED,
            parsing_confidence=0.92,
            extracted_skills=[{"name": "Docker"}, {"name": "Kubernetes"}, {"name": "Linux"}],
            extracted_projects=[{"title": "Kubernetes Production Cluster Setup"}],
            extracted_experience=[{"role": "DevOps Specialist", "company": "Beta Cloud"}],
            extracted_education=[]
        )
        db_session.add(r1)
        db_session.add(r2)
        db_session.commit()

        overview = await LearningPlanService.build_personalized_learning_overview(
            user_id=user.id,
            db=db_session,
            include_youtube=False
        )

        assert overview["is_onboarding_empty_state"] is False
        # Aggregated skills from both resumes
        known = set(overview["candidate_known_skills"])
        assert "Python" in known
        assert "FastAPI" in known
        assert "Docker" in known
        assert "Kubernetes" in known
        assert "Linux" in known

        # Aggregated roles from both resumes
        roles = overview["target_roles"]
        assert "Backend Developer" in roles
        assert "DevOps Engineer" in roles

        # Both experiences aggregated
        exp_roles = [e["role"] for e in overview["candidate_experience"]]
        assert "Backend Engineer" in exp_roles
        assert "DevOps Specialist" in exp_roles

        # HTTP API check
        token = create_access_token(user.id)
        res = client.get("/api/v1/learning/overview", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
    finally:
        db_session.close = orig_close


def test_api_projects_endpoint_with_resume_data(db_session, client):
    """
    Verifies that GET /api/v1/learning/projects returns HTTP 200 and incorporates
    resume facts and deduplicates against resume projects.
    """
    orig_close = db_session.close
    db_session.close = lambda: None
    try:
        user = User(
            email=f"projects_api_user_{int(time.time() * 1000)}@outreachiq.ai",
            full_name="Projects API User",
            hashed_password="pw_test_dummy",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        # Add resume
        resume = Resume(
            user_id=user.id,
            title="Python Developer Resume",
            target_role="Backend Developer",
            is_preferred=True,
            is_active=True,
            filename="python_dev.pdf",
            original_filename="python_dev.pdf",
            file_path="/uploads/python_dev.pdf",
            file_size=12000,
            mime_type="application/pdf",
            parsed_text="Python Backend Engineer with PostgreSQL experience",
            parsing_status=ParsingStatus.PARSED,
            parsing_confidence=0.9,
            extracted_skills=[{"name": "Python"}, {"name": "SQL"}],
            extracted_projects=[{"title": "High-Throughput Asynchronous Task Processing Engine"}],
            extracted_experience=[],
            extracted_education=[]
        )
        db_session.add(resume)
        db_session.commit()

        token = create_access_token(user.id)
        res = client.get("/api/v1/learning/projects", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        blueprints = res.json()
        assert len(blueprints) > 0

        # Existing project should be deduplicated
        titles = [b["title"] for b in blueprints]
        assert "High-Throughput Asynchronous Task Processing Engine" not in titles
    finally:
        db_session.close = orig_close
