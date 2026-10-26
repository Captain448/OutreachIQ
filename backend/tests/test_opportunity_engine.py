from app.services.opportunity_normalizer import OpportunityNormalizer
from app.services.opportunity_deduplicator import OpportunityDeduplicator
from app.services.company_research_service import CompanyResearchService
from app.services.matching_service import MatchingService
from app.services.listing_extractor import ListingExtractor
from app.services.discovery_query_builder import DiscoveryQueryBuilder
from app.services.providers.base_provider import NormalizedJob, NormalizedCompany, CompanySignalItem
from app.models.opportunity import OpportunityType, RecommendedAction
from app.schemas.intelligence import (
    CandidateIntelligenceRepresentation,
    CandidateIdentity,
    CategorizedSkill,
    CompletenessMetric
)
from app.models.profile import SkillStatus


def test_opportunity_normalizer():
    # Title normalization
    assert OpportunityNormalizer.normalize_title("Sr. Software Dev (Remote)") == "Senior Software Developer"
    assert OpportunityNormalizer.normalize_title("Lead SWE - Platform Team") == "Lead Software Engineer"
    assert OpportunityNormalizer.normalize_title("Jr. ML Engineer [Bengaluru]") == "Junior Machine Learning Engineer"

    # Skill extraction with word boundary check
    text = "Must be experienced with Python, FastAPI, and Docker. Experience with React and PostgreSQL is a plus."
    skills = OpportunityNormalizer.extract_skills_from_text(text)
    assert "Python" in skills
    assert "fastapi" in skills
    assert "Docker" in skills
    assert "React" in skills
    assert "Postgresql" in skills

    # Work arrangement detection
    arr, is_remote = OpportunityNormalizer.detect_work_arrangement("Backend Dev", "Work from home full time", "Remote")
    assert arr == "remote"
    assert is_remote is True

    arr2, is_remote2 = OpportunityNormalizer.detect_work_arrangement("Office Lead", "Onsite 5 days a week", "Mumbai")
    assert arr2 == "onsite"
    assert is_remote2 is False


def test_opportunity_deduplication():
    job1 = NormalizedJob(
        title="Senior Python Engineer",
        company_name="Acme Corp",
        description="Python FastAPI backend role",
        location="Bengaluru",
        is_remote=False,
        work_arrangement="hybrid",
        employment_type="full-time",
        primary_url="https://linkedin.com/jobs/view/101?utm_source=feed",
        source_name="LinkedIn",
        source_provider="tavily",
        extracted_skills=["Python", "FastAPI"]
    )
    job2 = NormalizedJob(
        title="Sr. Python Engineer",  # Normalizes to Senior Python Engineer
        company_name="Acme Corp",
        description="Python FastAPI backend role with Docker and Kubernetes",
        location="Bengaluru",
        is_remote=False,
        work_arrangement="hybrid",
        employment_type="full-time",
        primary_url="https://indeed.com/viewjob?jk=101",
        source_name="Indeed",
        source_provider="jsearch",
        extracted_skills=["Docker", "Kubernetes"]
    )

    deduped = OpportunityDeduplicator.deduplicate_jobs([job1, job2])
    assert len(deduped) == 1
    merged = deduped[0]
    assert "LinkedIn" in merged.source_name
    assert "Indeed" in merged.source_name
    assert "Python" in merged.extracted_skills
    assert "Docker" in merged.extracted_skills
    assert "Kubernetes" in merged.extracted_skills


def test_company_signal_evaluation_types():
    # 1. Company with advertised job -> ADVERTISED
    comp_adv = NormalizedCompany(
        name="TechNova",
        source_name="Web",
        source_provider="tavily",
        source_url="https://technova.io",
        signals=[]
    )
    res_adv = CompanyResearchService.evaluate_company_signals(
        company=comp_adv,
        candidate_skills=["Python", "Docker"],
        candidate_roles=["Backend Engineer"],
        candidate_industries=["Cloud"],
        has_advertised_jobs=True
    )
    assert res_adv["opportunity_type"] == OpportunityType.ADVERTISED

    # 2. Company with funding/expansion signal + candidate skill match -> EMERGING
    signal = CompanySignalItem(
        signal_type="funding_expansion",
        headline="TechNova raises $15M Series A to expand Python cloud platform",
        evidence_url="https://techcrunch.com/technova"
    )
    comp_emerging = NormalizedCompany(
        name="TechNova",
        description="Building cloud platforms with Python and Docker",
        source_name="Tavily",
        source_provider="tavily",
        source_url="https://technova.io",
        signals=[signal]
    )
    res_emerging = CompanyResearchService.evaluate_company_signals(
        company=comp_emerging,
        candidate_skills=["Python"],
        candidate_roles=["Backend Engineer"],
        candidate_industries=["Cloud"],
        has_advertised_jobs=False
    )
    assert res_emerging["opportunity_type"] == OpportunityType.EMERGING
    assert res_emerging["growth_signal_score"] >= 0.5
    assert "proactive" in res_emerging["why_contact"].lower()

    # 3. Company in industry but without immediate expansion signal -> STRATEGIC
    comp_strat = NormalizedCompany(
        name="QuietTech",
        description="Established boutique analytics consultancy",
        source_name="Exa",
        source_provider="exa",
        source_url="https://quiettech.com",
        signals=[]
    )
    res_strat = CompanyResearchService.evaluate_company_signals(
        company=comp_strat,
        candidate_skills=["Rust"],
        candidate_roles=["Rust Developer"],
        candidate_industries=["Analytics"],
        has_advertised_jobs=False
    )
    assert res_strat["opportunity_type"] == OpportunityType.STRATEGIC


def test_matching_service_scoring_and_actions():
    intel = CandidateIntelligenceRepresentation(
        identity=CandidateIdentity(full_name="Alex Dev"),
        education=[],
        work_experience=[],
        projects=[],
        verified_skills=[
            CategorizedSkill(name="Python", category="technical", status=SkillStatus.VERIFIED, source="test", confidence_score=1.0),
            CategorizedSkill(name="FastAPI", category="frameworks", status=SkillStatus.VERIFIED, source="test", confidence_score=1.0),
            CategorizedSkill(name="Docker", category="tools", status=SkillStatus.VERIFIED, source="test", confidence_score=1.0),
        ],
        inferred_skills=[],
        unverified_skills=[],
        preferences={"desired_roles": ["Backend Engineer"], "experience_level": "senior"},
        resume_inventory=[],
        career_directions=[],
        profile_completeness=CompletenessMetric(overall_percentage=90, missing_critical_fields=[], recommendations=[]),
        overall_confidence=0.95,
        evidence_grounding_summary="Verified candidate profile"
    )

    # High match job -> CONTACT_NOW
    job_high = NormalizedJob(
        title="Senior Backend Engineer",
        company_name="CloudCo",
        primary_url="https://cloudco.com/job1",
        source_name="LinkedIn",
        source_provider="tavily",
        extracted_skills=["Python", "FastAPI", "Docker"],
        location="Remote",
        is_remote=True,
        confidence=0.95
    )
    res_high = MatchingService.match_job(
        job=job_high,
        candidate_intel=intel,
        preferred_locations=["Remote"],
        remote_preference="remote",
        experience_level="senior"
    )
    assert res_high["match_score"] >= 0.70
    assert res_high["recommended_action"] == RecommendedAction.CONTACT_NOW
    assert len(res_high["matched_skills"]) >= 3

    # Critical failure: candidate is entry-level while job requires Lead/Staff leadership
    res_fail = MatchingService.match_job(
        job=job_high,
        candidate_intel=intel,
        preferred_locations=["Remote"],
        remote_preference="remote",
        experience_level="entry"  # Mismatch triggers critical failure
    )
    assert len(res_fail["critical_failures"]) >= 1
    assert res_fail["recommended_action"] == RecommendedAction.SKIP


def test_location_extractor_disambiguation():
    # Greater Noida vs Noida
    assert ListingExtractor._extract_location_from_text("Senior Engineer in Greater Noida, UP", "https://example.com/job1") == "Greater Noida"
    assert ListingExtractor._extract_location_from_text("Backend Developer at Sector 62, Noida office", "https://example.com/job2") == "Noida"
    
    # New Delhi vs Delhi
    assert ListingExtractor._extract_location_from_text("ML Engineer based in New Delhi", "https://example.com/job3") == "New Delhi"
    assert ListingExtractor._extract_location_from_text("Front-end lead in South Delhi area", "https://example.com/job4") == "Delhi"

    # Bengaluru / Bangalore
    assert ListingExtractor._extract_location_from_text("Full stack role in Bangalore", "https://example.com/job5") == "Bengaluru"
    assert ListingExtractor._extract_location_from_text("Staff Architect in Bengaluru", "https://example.com/job6") == "Bengaluru"

    # Gurugram / Gurgaon
    assert ListingExtractor._extract_location_from_text("DevOps Engineer, Cyber City Gurgaon", "https://example.com/job7") == "Gurugram"
    assert ListingExtractor._extract_location_from_text("Platform Lead, Gurugram", "https://example.com/job8") == "Gurugram"

    # Mohali
    assert ListingExtractor._extract_location_from_text("Python Dev in Mohali Phase 8", "https://example.com/job9") == "Mohali"

    # Remote fallback
    assert ListingExtractor._extract_location_from_text("100% remote work from home position", "https://example.com/job10") == "Remote"


def test_discovery_query_builder_multi_location():
    queries = DiscoveryQueryBuilder.build_targeted_queries(
        target_roles=["AI/ML Engineer"],
        skills=["Python", "PyTorch"],
        locations=["Noida", "Gurugram"],
        work_arrangement="hybrid",
        employment_type="full-time",
        limit_queries=5
    )
    assert len(queries) > 0
    # Check that multi-location is joined as (Noida OR Gurugram)
    query_texts = [q["query"] for q in queries]
    assert any("Noida OR Gurugram" in qt or ("Noida" in qt and "Gurugram" in qt) for qt in query_texts)

    # Single location format
    single_queries = DiscoveryQueryBuilder.build_targeted_queries(
        target_roles=["Backend Engineer"],
        skills=["FastAPI"],
        locations=["Mohali"],
        limit_queries=2
    )
    assert any("Mohali" in q["query"] for q in single_queries)
