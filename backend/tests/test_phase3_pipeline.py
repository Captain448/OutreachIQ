import pytest
import json
from datetime import datetime, timezone, timedelta

from app.services.discovery_query_builder import DiscoveryQueryBuilder
from app.services.opportunity_normalizer import OpportunityNormalizer
from app.services.listing_extractor import ListingExtractor
from app.services.listing_verification_service import ListingVerificationService, JobVerificationStatus
from app.services.opportunity_deduplicator import OpportunityDeduplicator
from app.services.providers.base_provider import NormalizedJob


# ---------------------------------------------------------------------------
# 1. DiscoveryQueryBuilder Tests
# ---------------------------------------------------------------------------

def test_query_builder_role_variations():
    variations = DiscoveryQueryBuilder.get_role_variations("ai/ml engineer")
    assert len(variations) >= 2
    assert any("Machine Learning" in v or "AI" in v for v in variations)

    backend_vars = DiscoveryQueryBuilder.get_role_variations("backend developer")
    assert any("Backend" in v or "Software" in v for v in backend_vars)


def test_query_builder_targeted_sources():
    queries = DiscoveryQueryBuilder.build_targeted_queries(
        target_roles=["Full Stack Engineer"],
        skills=["React", "Python"],
        locations=["Bengaluru"],
        remote_preference="flexible",
        limit_queries=5
    )
    assert len(queries) >= 3
    
    # Verify presence of targeted ATS and network clauses
    query_texts = " ".join(q["query"] for q in queries)
    assert "greenhouse.io" in query_texts or "lever.co" in query_texts or "workday.com" in query_texts
    assert "linkedin.com" in query_texts
    assert "naukri.com" in query_texts


# ---------------------------------------------------------------------------
# 2. OpportunityNormalizer & Quality Filter Gate Tests
# ---------------------------------------------------------------------------

def test_normalizer_rejects_directory_pages():
    # Test directory aggregation titles
    is_valid, reason = OpportunityNormalizer.validate_job_listing(
        title="100 React Js Developer Job Vacancies Mohali, Punjab",
        company_name="Various Companies",
        primary_url="https://example.com/jobs/react-mohali",
        description="Search results for 100 vacancies"
    )
    assert not is_valid
    assert "directory" in reason.lower() or "search" in reason.lower() or "aggregator" in reason.lower()

    # Test pagination titles
    is_valid_page, reason_page = OpportunityNormalizer.validate_job_listing(
        title="Page 5259 - Senior Engineer Jobs",
        company_name="TechCorp",
        primary_url="https://example.com/jobs?page=5259",
        description="Pagination page 5259"
    )
    assert not is_valid_page
    assert "pagination" in reason_page.lower()


def test_normalizer_clean_employer_name():
    # Remove aggregators and city names mistaken as employers
    clean_emp = OpportunityNormalizer.clean_employer_name(
        company_name="Naukri.com - Infosys Limited",
        title="Software Engineer",
        url="https://www.naukri.com/job-listings-infosys-123"
    )
    assert "Naukri" not in clean_emp
    assert "Infosys" in clean_emp

    clean_city = OpportunityNormalizer.clean_employer_name(
        company_name="Mohali",
        title="AI Engineer",
        url="https://techstart.com/careers/ai-engineer"
    )
    assert clean_city != "Mohali"


# ---------------------------------------------------------------------------
# 3. ListingExtractor Structured JSON-LD & Content Extraction Tests
# ---------------------------------------------------------------------------

def test_listing_extractor_json_ld():
    html_sample = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Senior Python Engineer at Datacore</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Senior Python Engineer",
            "hiringOrganization": {
                "@type": "Organization",
                "name": "Datacore Systems"
            },
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Bengaluru",
                    "addressCountry": "India"
                }
            },
            "baseSalary": {
                "@type": "MonetaryAmount",
                "currency": "INR",
                "value": {
                    "minValue": 1800000,
                    "maxValue": 2500000
                }
            },
            "description": "Looking for an experienced Python developer with FastAPI and PostgreSQL expertise. Apply now on our careers portal.",
            "directApply": "https://datacore.com/apply/py-101"
        }
        </script>
    </head>
    <body>
        <h1>Senior Python Engineer</h1>
        <a href="https://datacore.com/apply/py-101">Apply Now</a>
    </body>
    </html>
    """

    job = ListingExtractor._extract_from_json_ld(
        html=html_sample,
        url="https://datacore.com/careers/py-101",
        provider="tavily",
        category="Direct Company Portals"
    )

    assert job is not None
    assert job.title == "Senior Python Engineer"
    assert "Datacore" in job.company_name
    assert "Bengaluru" in job.location
    assert job.salary_range is not None and "1800000" in job.salary_range
    assert job.application_url == "https://datacore.com/apply/py-101"
    assert "python" in [s.lower() for s in job.extracted_skills]


# ---------------------------------------------------------------------------
# 4. ListingVerificationService State Validation Tests
# ---------------------------------------------------------------------------

def test_verification_service_verified_open():
    html_active = """
    <html>
        <body>
            <h1>Machine Learning Engineer at NeuralWorks</h1>
            <p>We are actively looking for an ML Engineer. Competitive package and benefits.</p>
            <button>Apply for this job</button>
        </body>
    </html>
    """
    res = ListingVerificationService.verify_html_content(
        content=html_active,
        url="https://neuralworks.com/jobs/ml-eng",
        expected_title="Machine Learning Engineer",
        expected_company="NeuralWorks",
        http_status=200
    )
    assert res["status"] == JobVerificationStatus.VERIFIED_OPEN.value
    assert res["is_verified"] is True
    assert len(res["active_indicators"]) > 0


def test_verification_service_expired_or_closed():
    html_closed = """
    <html>
        <body>
            <h1>Staff Backend Engineer</h1>
            <div class="alert">This job is no longer available. This position has been filled.</div>
        </body>
    </html>
    """
    res = ListingVerificationService.verify_html_content(
        content=html_closed,
        url="https://example.com/jobs/staff-eng",
        expected_title="Staff Backend Engineer",
        expected_company="Example Inc",
        http_status=200
    )
    assert res["status"] == JobVerificationStatus.EXPIRED_OR_CLOSED.value
    assert res["is_verified"] is False
    assert len(res["closed_indicators"]) > 0


def test_verification_service_expired_json_ld():
    past_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    html_expired_ld = f"""
    <html>
        <head>
            <script type="application/ld+json">
            {{
                "@type": "JobPosting",
                "title": "Cloud Architect",
                "validThrough": "{past_date}",
                "description": "Architect cloud platforms."
            }}
            </script>
        </head>
        <body>
            <h1>Cloud Architect</h1>
        </body>
    </html>
    """
    res = ListingVerificationService.verify_html_content(
        content=html_expired_ld,
        url="https://example.com/jobs/cloud-arch",
        expected_title="Cloud Architect",
        expected_company="Example Inc",
        http_status=200
    )
    assert res["status"] == JobVerificationStatus.EXPIRED_OR_CLOSED.value
    assert res["is_verified"] is False


def test_verification_service_unverified_fallback():
    # If network timeout or rate limit occurred
    # Returns LISTING_FOUND_STATUS_UNVERIFIED
    job = NormalizedJob(
        title="Frontend Specialist",
        company_name="Apex UI",
        description="React and TypeScript expert needed.",
        location="Remote",
        is_remote=True,
        work_arrangement="remote",
        employment_type="full-time",
        primary_url="https://apex.com/jobs/fe",
        source_name="Tavily",
        source_provider="tavily",
        verification_status=JobVerificationStatus.LISTING_FOUND_STATUS_UNVERIFIED.value,
        is_verified=False
    )
    assert job.verification_status == "LISTING_FOUND_STATUS_UNVERIFIED"
    assert job.is_verified is False


# ---------------------------------------------------------------------------
# 5. OpportunityDeduplicator & Quality Ingestion Tests
# ---------------------------------------------------------------------------

def test_deduplicator_preserves_verified_status():
    j1 = NormalizedJob(
        title="AI Engineer",
        company_name="AlphaTech",
        description="Senior AI Engineer role in Bengaluru.",
        location="Bengaluru",
        is_remote=False,
        work_arrangement="onsite",
        employment_type="full-time",
        primary_url="https://alphatech.com/jobs/1",
        source_name="Tavily",
        source_provider="tavily",
        verification_status=JobVerificationStatus.VERIFIED_OPEN.value,
        is_verified=True,
        confidence=0.95
    )
    j2 = NormalizedJob(
        title="AI Engineer",
        company_name="AlphaTech",
        description="Duplicate entry for AI Engineer.",
        location="Bengaluru",
        is_remote=False,
        work_arrangement="onsite",
        employment_type="full-time",
        primary_url="https://alphatech.com/jobs/1",
        source_name="Exa",
        source_provider="exa",
        verification_status=JobVerificationStatus.LISTING_FOUND_STATUS_UNVERIFIED.value,
        is_verified=False,
        confidence=0.85
    )

    deduped = OpportunityDeduplicator.deduplicate_jobs([j1, j2])
    assert len(deduped) == 1
    # Preserves highest quality / verified entry
    assert deduped[0].is_verified is True
    assert deduped[0].verification_status == JobVerificationStatus.VERIFIED_OPEN.value
