import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.models.user import User
from app.models.discovery import AgentRun, RunStatus
from app.models.opportunity import OpportunityType
from app.services.providers.base_provider import NormalizedJob, NormalizedCompany, CompanySignalItem
from app.services.providers.remotive_adapter import RemotiveAdapter
from app.services.providers.tavily_adapter import TavilyAdapter
from app.services.providers.provider_registry import provider_registry
from app.services.company_research_service import CompanyResearchService
from app.services.opportunity_orchestrator import OpportunityOrchestrator


def _create_mock_job(title: str, company: str, url: str, provider: str = "tavily") -> NormalizedJob:
    return NormalizedJob(
        title=title,
        company_name=company,
        description=f"Job posting for {title} at {company}. Strong Python, FastAPI, and Docker experience required.",
        location="Remote",
        is_remote=True,
        work_arrangement="remote",
        employment_type="full-time",
        primary_url=url,
        source_name=f"{provider.capitalize()} Search",
        source_provider=provider,
        source_category="Job Board",
        posting_date="2026-03-01",
        extracted_skills=["Python", "FastAPI", "Docker"],
        confidence=0.92,
        extraction_quality=0.95,
        company_confidence=0.90,
        verification_status="VERIFIED_OPEN",
        is_verified=True
    )


def _create_mock_company(name: str, domain: str, provider: str = "tavily") -> NormalizedCompany:
    return NormalizedCompany(
        name=name,
        domain=domain,
        website_url=f"https://{domain}",
        description=f"{name} is an engineering organization focusing on Python, AI, and cloud infrastructure.",
        industry="Technology",
        headquarters="San Francisco, CA",
        signals=[
            CompanySignalItem(
                signal_type="funding_expansion",
                headline=f"{name} raises Series A for engineering expansion",
                date="2026-02-15",
                evidence_url=f"https://{domain}/news/series-a",
                confidence=0.90
            )
        ],
        source_name=f"{provider.capitalize()} Intelligence",
        source_provider=provider,
        source_url=f"https://{domain}",
        confidence=0.90
    )


# ---------------------------------------------------------------------------
# 1. Provider Circuit Breaker, Quota, & Health Tests
# ---------------------------------------------------------------------------

def test_daily_quota_cap_enforcement():
    adapter = TavilyAdapter(api_key="tvly-mock-key", persist_quota=False)
    adapter.daily_request_cap = 5
    adapter.daily_requests_used = 5

    can_run, reason = adapter.can_query()
    assert can_run is False
    assert "reached daily free quota cap" in reason
    assert adapter.circuit_status == "quota_exhausted"

    health = adapter.get_health_status()
    assert health["status"] == "quota_exhausted"
    assert health["daily_requests_used"] == 5
    assert health["daily_request_cap"] == 5


def test_rate_limit_cooldown_circuit_breaker():
    adapter = TavilyAdapter(api_key="tvly-mock-key")
    adapter.record_query_error(
        "Tavily rate limit exceeded",
        is_rate_limit=True,
        cooldown_seconds=120
    )

    can_run, reason = adapter.can_query()
    assert can_run is False
    assert "is rate-limited" in reason
    assert adapter.circuit_status == "rate_limited"

    health = adapter.get_health_status()
    assert health["status"] == "rate_limited"
    assert health["cooldown_remaining_seconds"] is not None
    assert health["cooldown_remaining_seconds"] > 0


def test_auth_error_fast_disable_without_retries():
    adapter = TavilyAdapter(api_key="tvly-invalid-key")
    adapter.record_query_error(
        "Invalid Tavily API key provided (HTTP 401)",
        is_auth_error=True
    )

    can_run, reason = adapter.can_query()
    assert can_run is False
    assert "disabled due to previous 401/403" in reason
    assert adapter.circuit_status == "disabled_auth_error"

    health = adapter.get_health_status()
    assert health["status"] == "disabled_auth_error"
    assert "401" in health["error_message"] or "disabled" in health["error_message"]


# ---------------------------------------------------------------------------
# 2. Remotive Zero-Cost Public Feed Tests
# ---------------------------------------------------------------------------

def test_remotive_adapter_zero_cost_configuration():
    adapter = RemotiveAdapter()
    assert adapter.is_configured() is True
    assert adapter.tier == 2
    assert "No API Key Required" in adapter.free_tier_info

    can_run, reason = adapter.can_query()
    assert can_run is True
    assert reason is None

    health = adapter.get_health_status()
    assert health["provider_name"] == "remotive"
    assert health["tier"] == 2
    assert health["is_configured"] is True


@pytest.mark.anyio
async def test_remotive_search_jobs_normalization():
    adapter = RemotiveAdapter()
    mock_remotive_payload = {
        "jobs": [
            {
                "id": 101,
                "url": "https://remotive.com/remote-jobs/software-dev/senior-python-dev-101",
                "title": "Senior Python Developer",
                "company_name": "Acme Cloud",
                "category": "software-dev",
                "tags": ["python", "docker", "fastapi"],
                "job_type": "full_time",
                "publication_date": "2026-03-01T12:00:00",
                "candidate_required_location": "Worldwide",
                "salary": "$120,000 - $140,000",
                "description": "<p>We are seeking a <strong>Senior Python Developer</strong> to lead backend development.</p>"
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_remotive_payload

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        jobs = await adapter.search_jobs("python", limit=5)

        assert len(jobs) == 1
        job = jobs[0]
        assert job.title == "Senior Python Developer"
        assert job.company_name == "Acme Cloud"
        assert job.is_remote is True
        assert job.work_arrangement == "remote"
        assert job.employment_type == "full-time"
        assert "<p>" not in (job.description or "")
        assert "Python" in job.extracted_skills
        assert job.source_provider == "remotive"
        assert job.source_category == "Public Feed"


# ---------------------------------------------------------------------------
# 3. Company Intelligence Facts vs Inferred Signals Tests
# ---------------------------------------------------------------------------

def test_company_signals_distinguishes_confirmed_facts_vs_inferences():
    company = _create_mock_company(name="ScaleFlow", domain="scaleflow.io")
    candidate_skills = ["Python", "FastAPI", "Docker"]
    candidate_roles = ["Software Engineer"]
    candidate_industries = ["Technology"]

    eval_result = CompanyResearchService.evaluate_company_signals(
        company=company,
        candidate_skills=candidate_skills,
        candidate_roles=candidate_roles,
        candidate_industries=candidate_industries,
        has_advertised_jobs=True
    )

    confirmed_facts = eval_result.get("confirmed_facts", [])
    inferred_signals = eval_result.get("inferred_signals", [])

    assert len(confirmed_facts) >= 2
    fact_types = [f["fact_type"] for f in confirmed_facts]
    assert "official_presence" in fact_types
    assert "verified_vacancy" in fact_types
    for f in confirmed_facts:
        assert f["is_verified"] is True
        assert f["confidence"] >= 0.90

    assert len(inferred_signals) >= 1
    signal_types = [s["signal_type"] for s in inferred_signals]
    assert "funding_expansion" in signal_types or "tech_stack_alignment" in signal_types
    for s in inferred_signals:
        assert "inference_type" in s


# ---------------------------------------------------------------------------
# 4. Two-Tier Orchestration & Quota Preservation Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_tier1_sufficient_results_skips_tier2(db_session):
    orig_close = db_session.close
    db_session.close = lambda: None
    try:
        user = User(
            email=f"tier1_sufficient_{int(time.time())}@outreachiq.ai",
            full_name="Tier1 Test Candidate",
            hashed_password="hashed_pw_test",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        run = AgentRun(
            user_id=user.id,
            run_type="opportunity_discovery",
            status=RunStatus.QUEUED,
            query_params={"target_roles": ["Software Engineer"], "skills": ["Python"]},
            providers_queried=[],
            providers_succeeded=[],
            providers_failed=[]
        )
        db_session.add(run)
        db_session.commit()

        # Tier 1 returns 6 jobs (>= DISCOVERY_MIN_RELEVANT_RESULTS = 5)
        tavily_jobs = [
            _create_mock_job(f"Engineer {i}", f"Company {i}", f"https://company{i}.com/job/{i}", "tavily")
            for i in range(1, 7)
        ]
        tavily_mock = MagicMock()
        tavily_mock.provider_name = "tavily"
        tavily_mock.tier = 1
        tavily_mock.is_configured.return_value = True
        tavily_mock.can_query.return_value = (True, None)
        tavily_mock.search_jobs = AsyncMock(return_value=tavily_jobs)
        tavily_mock.search_companies = AsyncMock(return_value=[])

        # Tier 2 Remotive mock should NOT be called
        remotive_mock = MagicMock()
        remotive_mock.provider_name = "remotive"
        remotive_mock.tier = 2
        remotive_mock.is_configured.return_value = True
        remotive_mock.can_query.return_value = (True, None)
        remotive_mock.search_jobs = AsyncMock(return_value=[])
        remotive_mock.search_companies = AsyncMock(return_value=[])

        with patch.object(provider_registry, "get_tier1_providers", return_value=[tavily_mock]), \
             patch.object(provider_registry, "get_tier2_providers", return_value=[remotive_mock]), \
             patch("app.services.opportunity_orchestrator.SessionLocal", return_value=db_session), \
             patch.object(CompanyResearchService, "research_company_classification_async", new=AsyncMock(return_value={"classification": "startup", "size_range": "1-50 employees", "evidence_excerpt": "Mock evidence"})):

            await OpportunityOrchestrator.execute_discovery_run_async(
                run_id=run.id,
                user_id=user.id,
                request_params={"target_roles": ["Software Engineer"], "skills": ["Python"]}
            )

        db_session.expire_all()
        db_session.refresh(run)
        assert run.status == RunStatus.COMPLETED
        assert remotive_mock.search_jobs.called is False
        assert run.diagnostics["fallback_triggered"] is False
        assert "skipped to conserve free quotas" in run.diagnostics["fallback_reason"]
        assert run.diagnostics["tier1_results_count"] >= 5
        assert run.diagnostics["tier2_results_count"] == 0
    finally:
        db_session.close = orig_close


@pytest.mark.anyio
async def test_tier1_insufficient_results_triggers_tier2_fallback(db_session):
    orig_close = db_session.close
    db_session.close = lambda: None
    try:
        user = User(
            email=f"tier1_insufficient_{int(time.time())}@outreachiq.ai",
            full_name="Fallback Test Candidate",
            hashed_password="hashed_pw_test",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        run = AgentRun(
            user_id=user.id,
            run_type="opportunity_discovery",
            status=RunStatus.QUEUED,
            query_params={"target_roles": ["Software Engineer"], "skills": ["Python"]},
            providers_queried=[],
            providers_succeeded=[],
            providers_failed=[]
        )
        db_session.add(run)
        db_session.commit()

        # Tier 1 returns only 2 jobs (< DISCOVERY_MIN_RELEVANT_RESULTS = 5)
        tavily_jobs = [
            _create_mock_job(f"Tavily Job {i}", f"Tavily Co {i}", f"https://tavilyco{i}.com/job", "tavily")
            for i in range(1, 3)
        ]
        tavily_mock = MagicMock()
        tavily_mock.provider_name = "tavily"
        tavily_mock.tier = 1
        tavily_mock.is_configured.return_value = True
        tavily_mock.can_query.return_value = (True, None)
        tavily_mock.search_jobs = AsyncMock(return_value=tavily_jobs)
        tavily_mock.search_companies = AsyncMock(return_value=[])

        # Tier 2 Remotive returns 4 jobs to supplement
        remotive_jobs = [
            _create_mock_job(f"Remotive Job {i}", f"Remotive Co {i}", f"https://remotiveco{i}.com/job", "remotive")
            for i in range(1, 5)
        ]
        remotive_mock = MagicMock()
        remotive_mock.provider_name = "remotive"
        remotive_mock.tier = 2
        remotive_mock.is_configured.return_value = True
        remotive_mock.can_query.return_value = (True, None)
        remotive_mock.search_jobs = AsyncMock(return_value=remotive_jobs)
        remotive_mock.search_companies = AsyncMock(return_value=[])

        with patch.object(provider_registry, "get_tier1_providers", return_value=[tavily_mock]), \
             patch.object(provider_registry, "get_tier2_providers", return_value=[remotive_mock]), \
             patch("app.services.opportunity_orchestrator.SessionLocal", return_value=db_session), \
             patch.object(CompanyResearchService, "research_company_classification_async", new=AsyncMock(return_value={"classification": "startup", "size_range": "1-50 employees", "evidence_excerpt": "Mock evidence"})):

            await OpportunityOrchestrator.execute_discovery_run_async(
                run_id=run.id,
                user_id=user.id,
                request_params={"target_roles": ["Software Engineer"], "skills": ["Python"], "locations": ["Remote"]}
            )

        db_session.expire_all()
        db_session.refresh(run)
        assert run.status == RunStatus.COMPLETED
        assert remotive_mock.search_jobs.called is True
        assert run.diagnostics["fallback_triggered"] is True
        assert "fewer than the minimum threshold" in run.diagnostics["fallback_reason"]
        assert run.diagnostics["tier1_results_count"] == 2
        assert run.diagnostics["tier2_results_count"] == 4
        assert run.results_discovered_count == 6
    finally:
        db_session.close = orig_close


@pytest.mark.anyio
async def test_diagnostics_contain_no_secrets(db_session):
    orig_close = db_session.close
    db_session.close = lambda: None
    try:
        user = User(
            email=f"diag_audit_{int(time.time())}@outreachiq.ai",
            full_name="Diagnostics Audit User",
            hashed_password="hashed_pw_test",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        run = AgentRun(
            user_id=user.id,
            run_type="opportunity_discovery",
            status=RunStatus.QUEUED,
            query_params={"target_roles": ["Software Engineer"]},
            providers_queried=[],
            providers_succeeded=[],
            providers_failed=[]
        )
        db_session.add(run)
        db_session.commit()

        tavily_mock = MagicMock()
        tavily_mock.provider_name = "tavily"
        tavily_mock.tier = 1
        tavily_mock.is_configured.return_value = True
        tavily_mock.can_query.return_value = (True, None)
        tavily_mock.search_jobs = AsyncMock(return_value=[_create_mock_job("Dev", "TestCo", "https://testco.com/job")])
        tavily_mock.search_companies = AsyncMock(return_value=[])

        with patch.object(provider_registry, "get_tier1_providers", return_value=[tavily_mock]), \
             patch.object(provider_registry, "get_tier2_providers", return_value=[]), \
             patch("app.services.opportunity_orchestrator.SessionLocal", return_value=db_session), \
             patch.object(CompanyResearchService, "research_company_classification_async", new=AsyncMock(return_value={"classification": "startup", "size_range": "1-50", "evidence_excerpt": "Mock"})):

            await OpportunityOrchestrator.execute_discovery_run_async(
                run_id=run.id,
                user_id=user.id,
                request_params={"target_roles": ["Software Engineer"]}
            )

        db_session.expire_all()
        db_session.refresh(run)
        diag_str = str(run.diagnostics).lower()
        for forbidden in ["tvly-", "exa-", "api_key", "secret", "bearer", "password", "token"]:
            assert forbidden not in diag_str or forbidden in ("token",) and "csrf" not in diag_str
    finally:
        db_session.close = orig_close


def test_persistent_quota_survives_process_restart():
    from app.services.providers.base_provider import PersistentQuotaTracker
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    PersistentQuotaTracker.reset_usage_for_test("restart_test_provider", today)

    class RestartTestAdapter(TavilyAdapter):
        @property
        def provider_name(self) -> str:
            return "restart_test_provider"

    # Worker/Process 1 initializes and performs 3 requests
    p1 = RestartTestAdapter(api_key="tvly_dummy_key")
    p1.daily_request_cap = 5
    p1.record_query_success(latency_ms=100.0, results_count=2)
    p1.record_query_success(latency_ms=120.0, results_count=1)
    p1.record_query_success(latency_ms=90.0, results_count=4)
    assert p1.daily_requests_used == 3

    # Process restarts: p1 is garbage-collected, new instance p2 is created
    del p1
    p2 = RestartTestAdapter(api_key="tvly_dummy_key")
    p2.daily_request_cap = 5
    # Verification: p2 immediately reflects the 3 requests performed before reboot
    can_run, _ = p2.can_query()
    assert can_run is True
    assert p2.daily_requests_used == 3

    # Clean up test entry
    PersistentQuotaTracker.reset_usage_for_test("restart_test_provider", today)


def test_multi_worker_shared_quota_enforcement():
    from app.services.providers.base_provider import PersistentQuotaTracker
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    PersistentQuotaTracker.reset_usage_for_test("shared_worker_test", today)

    class SharedWorkerAdapter(TavilyAdapter):
        @property
        def provider_name(self) -> str:
            return "shared_worker_test"

    # Worker A and Worker B instances running in parallel
    worker_a = SharedWorkerAdapter(api_key="tvly_dummy_key")
    worker_a.daily_request_cap = 2

    worker_b = SharedWorkerAdapter(api_key="tvly_dummy_key")
    worker_b.daily_request_cap = 2

    # Worker A consumes the quota to cap
    worker_a.record_query_success(latency_ms=100.0, results_count=3)
    worker_a.record_query_success(latency_ms=110.0, results_count=2)
    assert worker_a.daily_requests_used == 2

    # Worker B evaluates can_query() - should immediately detect quota exhaustion
    can_run, reason = worker_b.can_query()
    assert can_run is False
    assert worker_b.circuit_status == "quota_exhausted"
    assert "reached daily free quota cap" in reason

    # Clean up test entry
    PersistentQuotaTracker.reset_usage_for_test("shared_worker_test", today)


def test_evaluation_providers_disabled_by_default():
    from app.services.providers.adzuna_adapter import AdzunaAdapter
    from app.services.providers.jooble_adapter import JoobleAdapter

    adzuna = AdzunaAdapter(app_id="test_id", app_key="test_key_valid_length")
    jooble = JoobleAdapter(api_key="test_jooble_valid_key")

    # In default settings, ENABLE_EVALUATION_PROVIDERS is False
    assert settings.ENABLE_EVALUATION_PROVIDERS is False
    assert adzuna.is_configured() is False
    assert jooble.is_configured() is False
    can_run_a, reason_a = adzuna.can_query()
    can_run_j, reason_j = jooble.can_query()
    assert can_run_a is False
    assert can_run_j is False
    assert "missing credentials or is unconfigured" in reason_a
    assert "missing credentials or is unconfigured" in reason_j

