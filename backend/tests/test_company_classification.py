import uuid
from datetime import datetime, timezone
import pytest
from app.models.company import Company
from app.models.opportunity import Opportunity, OpportunityType, OpportunityStatus, RecommendedAction
from app.models.user import User
from app.schemas.company import CompanyRead
from app.services.company_research_service import CompanyResearchService
from app.services.opportunity_normalizer import OpportunityNormalizer


def test_classification_all_categories():
    # 1. Enterprise (known titan)
    res_ent = CompanyResearchService.research_company_classification(company_name="Google")
    assert res_ent["classification"] == "enterprise"
    assert "employees" in (res_ent["size_range"] or "")
    assert res_ent["confidence"] >= 0.90

    # 2. Mid-sized (explicit 500-2000 headcount in description)
    res_mid = CompanyResearchService.research_company_classification(
        company_name="Apex Global Logistics",
        existing_description="Fast-growing mid-market supply chain platform with 1,200 employees across 4 regional hubs."
    )
    assert res_mid["classification"] == "mid_sized"
    assert "employees" in (res_mid["size_range"] or "")

    # 3. SMB (boutique agency / 50-200 employees)
    res_smb = CompanyResearchService.research_company_classification(
        company_name="PixelCraft Studio",
        existing_description="Boutique agency and consulting firm with 75 employees specializing in custom UI/UX design."
    )
    assert res_smb["classification"] == "smb"

    # 4. Startup (seed funded / early stage / 1-50 employees)
    res_start = CompanyResearchService.research_company_classification(
        company_name="NeuroSync AI",
        existing_description="Early-stage seed funded startup building neuromorphic computing frameworks with 15 employees."
    )
    assert res_start["classification"] == "startup"

    # 5. Unknown (insufficient public evidence - honest fallback)
    res_unk = CompanyResearchService.research_company_classification(
        company_name="Xyzzqwk Unobtanium 99999",
        existing_description=None
    )
    assert res_unk["classification"] == "unknown"
    assert res_unk["size_range"] is None


def test_research_caching():
    CompanyResearchService.clear_cache()
    assert CompanyResearchService.get_cache_size() == 0

    # First lookup
    res1 = CompanyResearchService.research_company_classification(company_name="Microsoft")
    assert res1["classification"] == "enterprise"
    assert CompanyResearchService.get_cache_size() == 1

    # Second lookup should hit cache
    res2 = CompanyResearchService.research_company_classification(company_name="Microsoft")
    assert res2 == res1
    assert CompanyResearchService.get_cache_size() == 1


def test_normalizer_employer_cleaning():
    # 1. Distinguish company from location in Naukri URL
    url_mohali = "https://www.naukri.com/job-listings-mern-stack-developer-relinns-technologies-mohali-1-to-4-years-060225502955"
    cleaned = OpportunityNormalizer.clean_employer_name(
        company_name="Mohali",
        title="MERN Stack Developer",
        url=url_mohali
    )
    assert cleaned == "Relinns Technologies"

    # 2. Extract true employer from Naukri aggregator name
    url_visio = "https://www.naukri.com/job-listings-ai-ml-engineer-with-knowledge-of-front-end-visioapps-technology-gurugram-0-to-4-years-131026036420"
    cleaned_naukri = OpportunityNormalizer.clean_employer_name(
        company_name="Naukri",
        title="AI/ML Engineer",
        url=url_visio
    )
    assert cleaned_naukri == "Visioapps Technology"

    # 3. Clean pagination headings
    url_iweb = "https://www.naukri.com/iweb-technologies-jobs-5259"
    cleaned_page = OpportunityNormalizer.clean_employer_name(
        company_name="Page 5259",
        title="Software Engineer",
        url=url_iweb
    )
    assert cleaned_page == "Iweb Technologies"

    # 4. Clean title with 'at <Company>'
    cleaned_title = OpportunityNormalizer.clean_employer_name(
        company_name="Internshala",
        title="Python Developer at Zeta Systems",
        url="https://internshala.com/internships/python-developer"
    )
    assert cleaned_title == "Zeta Systems"


def test_company_schema_serialization():
    now = datetime.now(timezone.utc)
    comp = Company(
        id=str(uuid.uuid4()),
        name="Stripe",
        domain="stripe.com",
        classification="enterprise",
        size_range="5,000+ employees",
        growth_signal_score=0.8,
        alignment_score=0.9,
        signals_data=[],
        has_advertised_openings=True,
        created_at=now,
        updated_at=now
    )
    read_schema = CompanyRead.model_validate(comp)
    assert read_schema.classification == "enterprise"
    assert read_schema.size_range == "5,000+ employees"


def test_api_filtering_by_classification(client, db_session):
    # 1. Register test user
    reg = client.post(
        "/auth/register",
        json={"email": "class.tester@example.com", "password": "Password123!", "full_name": "Classification Tester"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.query(User).filter(User.email == "class.tester@example.com").first()

    # Create test companies with different classifications
    c_ent = Company(
        id=str(uuid.uuid4()),
        name="Enterprise Corp",
        domain="enterprise.com",
        classification="enterprise",
        size_range="10,000+ employees",
        signals_data=[],
        has_advertised_openings=True
    )
    c_start = Company(
        id=str(uuid.uuid4()),
        name="Startup Innovations",
        domain="startup.com",
        classification="startup",
        size_range="1-20 employees",
        signals_data=[],
        has_advertised_openings=True
    )
    c_unk = Company(
        id=str(uuid.uuid4()),
        name="Unspecified Entity",
        domain="unspecified.com",
        classification="unknown",
        signals_data=[],
        has_advertised_openings=True
    )
    db_session.add_all([c_ent, c_start, c_unk])
    db_session.commit()

    # Create opportunities
    opp_ent = Opportunity(
        id=str(uuid.uuid4()),
        user_id=user.id,
        company_id=c_ent.id,
        opportunity_type=OpportunityType.ADVERTISED,
        status=OpportunityStatus.ACTIVE,
        match_score=0.90,
        evidence_confidence=0.95,
        recommended_action=RecommendedAction.CONTACT_NOW
    )
    opp_start = Opportunity(
        id=str(uuid.uuid4()),
        user_id=user.id,
        company_id=c_start.id,
        opportunity_type=OpportunityType.ADVERTISED,
        status=OpportunityStatus.ACTIVE,
        match_score=0.85,
        evidence_confidence=0.90,
        recommended_action=RecommendedAction.CONTACT_NOW
    )
    opp_unk = Opportunity(
        id=str(uuid.uuid4()),
        user_id=user.id,
        company_id=c_unk.id,
        opportunity_type=OpportunityType.ADVERTISED,
        status=OpportunityStatus.ACTIVE,
        match_score=0.60,
        evidence_confidence=0.50,
        recommended_action=RecommendedAction.IMPROVE_FIRST
    )
    db_session.add_all([opp_ent, opp_start, opp_unk])
    db_session.commit()

    # Filter enterprise
    res = client.get("/opportunities?company_classification=enterprise", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["company"]["classification"] == "enterprise"

    # Filter startup
    res = client.get("/opportunities?company_classification=startup", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["company"]["classification"] == "startup"

    # Filter unknown
    res = client.get("/opportunities?company_classification=unknown", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["company"]["classification"] == "unknown"
