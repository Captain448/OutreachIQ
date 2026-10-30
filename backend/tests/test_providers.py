import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from app.services.providers.tavily_adapter import TavilyAdapter
from app.services.providers.exa_adapter import ExaAdapter
from app.services.providers.base_provider import NormalizedJob, NormalizedCompany


@pytest.mark.anyio
async def test_tavily_adapter_success():
    adapter = TavilyAdapter(api_key="tvly-mock-valid-key")
    assert adapter.is_configured() is True

    mock_response = {
        "results": [
            {
                "title": "Senior Python Engineer at Stripe",
                "url": "https://stripe.com/jobs/123",
                "content": "We are seeking a Senior Python Engineer experienced in FastAPI, Docker, and PostgreSQL. Remote in India.",
                "score": 0.95
            }
        ]
    }
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("app.services.listing_extractor.ListingExtractor.fetch_page_content", new_callable=AsyncMock, return_value=None):
        mock_post.return_value = mock_resp
        jobs = await adapter.search_jobs(query="Python Engineer", location="India", limit=5)
        
        assert len(jobs) == 1
        job = jobs[0]
        assert job.title == "Senior Python Engineer"
        assert job.company_name == "Stripe"
        assert job.is_remote is True
        assert "Fastapi" in [s.title() for s in job.extracted_skills]
        assert job.source_provider == "tavily"
        assert job.confidence >= 0.9


@pytest.mark.anyio
async def test_tavily_adapter_invalid_key_and_quota_error():
    adapter = TavilyAdapter(api_key="tvly-bad-key")
    
    # 401 Invalid Key
    mock_401 = MagicMock()
    mock_401.status_code = 401
    mock_401.text = "Unauthorized"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_401
        jobs = await adapter.search_jobs(query="Engineer")
        assert len(jobs) == 0
        health = adapter.get_health_status()
        assert health["status"] in ("error", "disabled_auth_error")
        assert health["circuit_status"] == "disabled_auth_error"
        assert "Invalid Tavily API key" in health["error_message"] or "401/403" in health["error_message"]

    # 429 Quota Exhausted
    adapter2 = TavilyAdapter(api_key="tvly-quota-key")
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.text = "Rate Limit Exceeded"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_429
        jobs2 = await adapter2.search_jobs(query="Engineer")
        assert len(jobs2) == 0
        health2 = adapter2.get_health_status()
        assert health2["status"] in ("error", "rate_limited")
        assert health2["circuit_status"] == "rate_limited"
        assert "quota" in health2["error_message"].lower() or "rate" in health2["error_message"].lower()


@pytest.mark.anyio
async def test_exa_adapter_success_and_company_discovery():
    adapter = ExaAdapter(api_key="exa-mock-key")
    assert adapter.is_configured() is True

    mock_job_response = {
        "results": [
            {
                "title": "Machine Learning Engineer - Anthropic",
                "url": "https://anthropic.com/careers/ml",
                "text": "Building next-generation safety models using PyTorch, Kubernetes, and Python.",
                "highlights": ["Strong experience with PyTorch and distributed training."],
                "score": 0.96,
                "publishedDate": "2026-03-01"
            }
        ]
    }
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_job_response

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("app.services.listing_extractor.ListingExtractor.fetch_page_content", new_callable=AsyncMock, return_value=None):
        mock_post.return_value = mock_resp
        jobs = await adapter.search_jobs(query="Machine Learning", location="Remote", limit=5)
        assert len(jobs) == 1
        assert jobs[0].company_name == "Anthropic"
        assert "Pytorch" in [s.title() for s in jobs[0].extracted_skills]

    # Test company semantic discovery
    mock_comp_response = {
        "results": [
            {
                "title": "Modal Labs - Serverless GPU Cloud",
                "url": "https://modal.com",
                "text": "Modal is a developer platform running Python, PyTorch, and Docker workloads at scale.",
                "highlights": ["Announcing our series B expansion and engineering hiring."],
                "score": 0.92,
                "publishedDate": "2026-02-15"
            }
        ]
    }
    mock_comp_resp = MagicMock()
    mock_comp_resp.status_code = 200
    mock_comp_resp.json.return_value = mock_comp_response

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_comp_resp
        companies = await adapter.search_companies(skills=["PyTorch", "Python"], industries=["AI"], roles=["Engineer"])
        assert len(companies) == 1
        assert "Modal" in companies[0].name
        assert len(companies[0].signals) >= 1
        assert companies[0].signals[0].signal_type == "product_and_technology_alignment"


@pytest.mark.anyio
async def test_one_provider_failing_while_other_succeeds():
    """
    Test resilience: Tavily fails (500), but Exa succeeds (200).
    System returns partial results cleanly without crashing.
    """
    tavily = TavilyAdapter(api_key="tvly-mock-fail")
    exa = ExaAdapter(api_key="exa-mock-ok")

    mock_500 = MagicMock()
    mock_500.status_code = 500
    mock_500.text = "Internal Server Error"

    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.json.return_value = {
        "results": [{
            "title": "Backend Architect - Databricks",
            "url": "https://databricks.com/jobs/backend",
            "text": "Seeking Backend Architect with Go and Kubernetes.",
            "highlights": ["Go and Kubernetes required."],
            "score": 0.90
        }]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_500
        tavily_jobs = await tavily.search_jobs("Architect")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_200
        exa_jobs = await exa.search_jobs("Architect")

    assert len(tavily_jobs) == 0
    assert len(exa_jobs) == 1
    assert exa_jobs[0].company_name == "Databricks"
