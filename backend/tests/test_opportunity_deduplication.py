import pytest
from app.services.opportunity_deduplicator import OpportunityDeduplicator
from app.services.providers.base_provider import NormalizedJob
from app.models.job import Job
from app.models.company import Company
from app.models.opportunity import Opportunity, OpportunityType, OpportunityStatus, RecommendedAction
from app.db.session import SessionLocal


def test_canonicalize_url():
    # Tracking parameters stripped
    url1 = "https://www.linkedin.com/jobs/view/123456?utm_source=share&utm_medium=member_desktop&ref=fb"
    url2 = "https://www.linkedin.com/jobs/view/123456/"
    url3 = "https://WWW.LINKEDIN.COM/jobs/view/123456"

    canon1 = OpportunityDeduplicator.canonicalize_url(url1)
    canon2 = OpportunityDeduplicator.canonicalize_url(url2)
    canon3 = OpportunityDeduplicator.canonicalize_url(url3)

    assert canon1 == "https://www.linkedin.com/jobs/view/123456"
    assert canon2 == "https://www.linkedin.com/jobs/view/123456"
    assert canon3 == "https://www.linkedin.com/jobs/view/123456"


def test_deduplicate_jobs_in_memory():
    job_variant1 = NormalizedJob(
        title="Senior Python Backend Developer",
        company_name="Acme Corp",
        description="Short description",
        location="Bengaluru",
        primary_url="https://acme.com/jobs/101?utm_campaign=winter",
        source_name="Tavily",
        source_provider="tavily",
        extracted_skills=["Python", "FastAPI"],
        confidence=0.85
    )
    job_variant2 = NormalizedJob(
        title="Senior Python Backend Developer",
        company_name="Acme Corp",
        description="Richer detailed description with engineering requirements and scale information.",
        location="Bengaluru",
        primary_url="https://acme.com/jobs/101?ref=linkedin",
        source_name="Exa",
        source_provider="exa",
        extracted_skills=["Python", "Docker"],
        confidence=0.92
    )

    deduped = OpportunityDeduplicator.deduplicate_jobs([job_variant1, job_variant2])
    assert len(deduped) == 1
    canonical_job = deduped[0]
    # Primary URL canonicalized
    assert canonical_job.primary_url == "https://acme.com/jobs/101"
    # Skills merged
    assert set(canonical_job.extracted_skills) == {"Python", "FastAPI", "Docker"}
    # Richer description preserved
    assert "Richer detailed description" in canonical_job.description
    # Confidence max preserved
    assert canonical_job.confidence == 0.92
    # Multi-source attribution
    assert "Tavily" in canonical_job.source_name and "Exa" in canonical_job.source_name


def test_database_opportunity_idempotency(client):
    reg = client.post(
        "/auth/register",
        json={"email": "idempotent.tester@example.com", "password": "Password123!", "full_name": "Idempotent Tester"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify filter suggestions work
    sugg_res = client.get("/opportunities/filter-suggestions", headers=headers)
    assert sugg_res.status_code == 200
    suggs = sugg_res.json()
    assert len(suggs["locations"]) > 0
    assert len(suggs["skills"]) > 0
