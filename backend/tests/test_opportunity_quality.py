import pytest
from app.services.opportunity_normalizer import OpportunityNormalizer
from app.services.opportunity_deduplicator import OpportunityDeduplicator
from app.services.matching_service import MatchingService
from app.services.providers.base_provider import NormalizedJob
from app.models.opportunity import RecommendedAction
from app.schemas.intelligence import (
    CandidateIntelligenceRepresentation,
    CandidateIdentity,
    CategorizedSkill,
    CompletenessMetric
)
from app.models.profile import SkillStatus


def test_quality_gate_rejects_pagination_and_numeric_titles():
    # 1. Page numbers
    is_valid, reason = OpportunityNormalizer.validate_job_listing(
        title="Page 5259",
        company_name="Tech Corp",
        primary_url="https://example.com/jobs/5259"
    )
    assert not is_valid
    assert "pagination" in reason.lower()

    # 2. Page X of Y
    is_valid, reason = OpportunityNormalizer.validate_job_listing(
        title="Page 2 of 10",
        company_name="Tech Corp",
        primary_url="https://example.com/page2"
    )
    assert not is_valid

    # 3. Numeric only
    is_valid, reason = OpportunityNormalizer.validate_job_listing(
        title="404",
        company_name="Tech Corp",
        primary_url="https://example.com/404"
    )
    assert not is_valid
    assert "numeric" in reason.lower()


def test_quality_gate_rejects_directory_aggregations_and_fragments():
    # 1. Search aggregator directory listings with counts
    is_valid, reason = OpportunityNormalizer.validate_job_listing(
        title="203 C Engineer Job Vacancies In Mohali",
        company_name="Naukri",
        primary_url="https://naukri.com/c-engineer-jobs-in-mohali"
    )
    assert not is_valid
    assert "directory" in reason.lower() or "search" in reason.lower()

    is_valid, reason = OpportunityNormalizer.validate_job_listing(
        title="100 React Js Developer Job Vacancies Mohali, Punjab",
        company_name="Naukri",
        primary_url="https://naukri.com/react-jobs"
    )
    assert not is_valid

    is_valid, reason = OpportunityNormalizer.validate_job_listing(
        title="40 Machine Learning Work From Home Fresher Jobs in ...",
        company_name="Internshala",
        primary_url="https://internshala.com/ml-jobs"
    )
    assert not is_valid

    # 2. Generic company jobs directory heading
    is_valid, reason = OpportunityNormalizer.validate_job_listing(
        title="Pione Technologies Llp Jobs",
        company_name="Pione Technologies",
        primary_url="https://example.com/jobs"
    )
    assert not is_valid
    assert "directory heading" in reason.lower()

    # 3. Navigation text
    is_valid, reason = OpportunityNormalizer.validate_job_listing(
        title="Search Jobs - Career Portal",
        company_name="Example Inc",
        primary_url="https://example.com/search"
    )
    assert not is_valid


def test_quality_gate_rejects_invalid_urls():
    # Missing scheme or malformed
    is_valid, reason = OpportunityNormalizer.validate_job_listing(
        title="Machine Learning Engineer",
        company_name="OpenAI",
        primary_url="javascript:void(0)"
    )
    assert not is_valid
    assert "url" in reason.lower()

    is_valid, reason = OpportunityNormalizer.validate_job_listing(
        title="Machine Learning Engineer",
        company_name="OpenAI",
        primary_url="ftp://ftp.example.com/job"
    )
    assert not is_valid


def test_quality_gate_accepts_valid_jobs_even_with_missing_optional_fields():
    # Valid job without location, without description
    is_valid, reason = OpportunityNormalizer.validate_job_listing(
        title="AI/ML Engineer",
        company_name="DeepMind",
        primary_url="https://deepmind.google/careers/123",
        description=None
    )
    assert is_valid
    assert reason is None

    # Valid internship
    is_valid, reason = OpportunityNormalizer.validate_job_listing(
        title="Machine Learning Research Intern",
        company_name="Microsoft Research",
        primary_url="https://careers.microsoft.com/us/en/job/456"
    )
    assert is_valid


def test_employer_cleaning_from_aggregators():
    # When aggregator name is passed, extract real company from title or domain
    clean_emp = OpportunityNormalizer.clean_employer_name(
        company_name="Naukri",
        title="Senior AI Engineer at GreyB Services in Mohali",
        url="https://naukri.com/job-123"
    )
    assert "GreyB" in clean_emp

    clean_emp2 = OpportunityNormalizer.clean_employer_name(
        company_name="Internshala",
        title="Deccan AI Experts hiring Junior ML Engineer",
        url="https://internshala.com/ml-intern"
    )
    assert "Deccan AI" in clean_emp2

    clean_emp3 = OpportunityNormalizer.clean_employer_name(
        company_name="Acme Corp Jobs",
        title="Backend Developer",
        url="https://acme.com/jobs"
    )
    assert clean_emp3 == "Acme Corp"


def test_company_classification_calibration():
    # Enterprise
    assert OpportunityNormalizer.classify_company("Google India") == "enterprise"
    assert OpportunityNormalizer.classify_company("Infosys Technologies") == "enterprise"
    assert OpportunityNormalizer.classify_company("Acme Global", "Fortune 500 enterprise leader") == "enterprise"

    # Startup
    assert OpportunityNormalizer.classify_company("StealthAI", "Y Combinator backed early-stage AI startup") == "startup"
    assert OpportunityNormalizer.classify_company("FinFlow", "Seed funded FinTech startup") == "startup"

    # SMB
    assert OpportunityNormalizer.classify_company("Local Design Studio", "Boutique agency specializing in UI") == "smb"

    # Unknown
    assert OpportunityNormalizer.classify_company("Apex Systems", "Discovered via public engineering listing.") == "unknown"


def test_match_score_calibration_prevents_misleading_81_percent():
    """
    CRITICAL TEST:
    Verifies that an AI/ML candidate matched against an unrelated role (.NET / Frontend / React)
    that only shares a generic skill (e.g. Python) CANNOT receive an 81% match score.
    """
    ai_candidate_intel = CandidateIntelligenceRepresentation(
        identity=CandidateIdentity(full_name="Aarav Sharma"),
        education=[],
        work_experience=[],
        projects=[],
        verified_skills=[
            CategorizedSkill(name="Python", category="languages", status=SkillStatus.VERIFIED, source="resume", confidence_score=1.0),
            CategorizedSkill(name="PyTorch", category="frameworks", status=SkillStatus.VERIFIED, source="resume", confidence_score=1.0),
            CategorizedSkill(name="Machine Learning", category="ai", status=SkillStatus.VERIFIED, source="resume", confidence_score=1.0),
            CategorizedSkill(name="NLP", category="ai", status=SkillStatus.VERIFIED, source="resume", confidence_score=1.0),
        ],
        inferred_skills=[],
        unverified_skills=[],
        preferences={"desired_roles": ["AI/ML Engineer", "Machine Learning Engineer"], "experience_level": "entry"},
        resume_inventory=[],
        career_directions=[],
        profile_completeness=CompletenessMetric(overall_percentage=90, missing_critical_fields=[], recommendations=[]),
        overall_confidence=0.95,
        evidence_grounding_summary="Candidate targeting AI/ML engineering positions."
    )

    # 1. Completely unrelated job (.NET Fresher Developer) that mentioned Python in text
    unrelated_job = NormalizedJob(
        title="Fresher .NET Developer",
        company_name="Kavita Tech",
        primary_url="https://example.com/net-job",
        source_name="LinkedIn",
        source_provider="tavily",
        extracted_skills=["Python"],  # Single matched skill
        location="Mohali",
        is_remote=False,
        work_arrangement="onsite",
        confidence=0.45
    )

    match_result = MatchingService.match_job(
        job=unrelated_job,
        candidate_intel=ai_candidate_intel,
        preferred_locations=["Mohali"],
        remote_preference="flexible",
        experience_level="entry"
    )

    # In previous bug: score was 0.81 (81%)!
    # In calibrated system: role relevance is low (0.10), so score is strictly capped <= 0.30
    assert match_result["match_score"] <= 0.30, f"Unrelated job scored {match_result['match_score']}, expected <= 0.30"
    assert match_result["recommended_action"] == RecommendedAction.SKIP

    # 2. Genuine AI/ML Engineer Job
    legit_job = NormalizedJob(
        title="Junior AI/ML Engineer",
        company_name="DeepInnovate",
        primary_url="https://deepinnovate.ai/careers/aiml",
        source_name="Company Portal",
        source_provider="tavily",
        extracted_skills=["Python", "PyTorch", "Machine Learning"],
        location="Mohali",
        is_remote=False,
        work_arrangement="hybrid",
        confidence=0.90
    )

    legit_result = MatchingService.match_job(
        job=legit_job,
        candidate_intel=ai_candidate_intel,
        preferred_locations=["Mohali"],
        remote_preference="flexible",
        experience_level="entry"
    )

    assert legit_result["match_score"] >= 0.75
    assert legit_result["recommended_action"] == RecommendedAction.CONTACT_NOW
    assert "AI/ML target" in legit_result["explanation"] or "Direct title match" in legit_result["explanation"]


def test_deduplicator_filters_junk_and_merges_records():
    junk_job = NormalizedJob(
        title="Page 5259",
        company_name="Naukri",
        primary_url="https://naukri.com/page5259",
        source_name="Naukri",
        source_provider="tavily"
    )
    valid_job_1 = NormalizedJob(
        title="Machine Learning Engineer",
        company_name="GreyB Services",
        primary_url="https://greyb.com/jobs/ml?utm_source=linkedin",
        source_name="LinkedIn",
        source_provider="tavily",
        extracted_skills=["Python", "PyTorch"]
    )
    valid_job_2 = NormalizedJob(
        title="ML Engineer",  # Canonicalizes to Machine Learning Engineer
        company_name="GreyB Services",
        primary_url="https://greyb.com/jobs/ml",  # Same canonical URL
        source_name="Company Portal",
        source_provider="tavily",
        extracted_skills=["NLP", "Docker"]
    )

    deduped = OpportunityDeduplicator.deduplicate_jobs([junk_job, valid_job_1, valid_job_2])
    # Junk job filtered out, valid jobs merged
    assert len(deduped) == 1
    assert deduped[0].company_name == "GreyB Services"
    assert "Python" in deduped[0].extracted_skills
    assert "NLP" in deduped[0].extracted_skills
