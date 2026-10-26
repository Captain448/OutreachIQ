from unittest.mock import patch, AsyncMock
from app.models.opportunity import OpportunityType, OpportunityStatus, RecommendedAction
from app.services.providers.base_provider import NormalizedJob, NormalizedCompany, CompanySignalItem


def test_opportunity_api_lifecycle(client):
    # 1. Register test user
    reg = client.post(
        "/auth/register",
        json={"email": "opp.tester@example.com", "password": "Password123!", "full_name": "Opportunity Tester"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Add profile preferences
    client.put(
        "/profile",
        json={
            "headline": "Lead Backend Architect",
            "preferences": {
                "desired_roles": ["Backend Engineer", "Software Architect"],
                "preferred_industries": ["Cloud Infrastructure"],
                "preferred_locations": ["Bengaluru", "Remote"],
                "remote_preference": "remote"
            },
            "skills": [
                {"name": "Python", "category": "technical", "status": "VERIFIED", "source": "USER_INPUT", "confidence_score": 1.0},
                {"name": "FastAPI", "category": "frameworks", "status": "VERIFIED", "source": "USER_INPUT", "confidence_score": 1.0}
            ]
        },
        headers=headers
    )

    # 2. Check Provider Health endpoint
    health_res = client.get("/providers/health", headers=headers)
    assert health_res.status_code == 200
    providers = health_res.json()
    assert len(providers) >= 4
    provider_names = [p["provider_name"] for p in providers]
    assert "tavily" in provider_names
    assert "exa" in provider_names
    assert "jsearch" in provider_names

    # 3. Mock provider results for discovery run
    mock_jobs = [
        NormalizedJob(
            title="Senior FastAPI Backend Developer",
            company_name="Zomato Labs",
            description="Developing high-throughput microservices using FastAPI, Python, and Docker in Bengaluru.",
            location="Bengaluru",
            is_remote=True,
            work_arrangement="remote",
            employment_type="full-time",
            primary_url="https://zomato.com/careers/fastapi-lead",
            source_name="Company Career Page",
            source_provider="tavily",
            extracted_skills=["Python", "FastAPI", "Docker"],
            evidence_excerpt="High-throughput microservices with FastAPI and Docker.",
            confidence=0.95
        )
    ]
    mock_comps = [
        NormalizedCompany(
            name="NeuroVector AI",
            domain="neurovector.io",
            website_url="https://neurovector.io",
            description="Autonomous vector database systems built in Python and Rust.",
            industry="Cloud Infrastructure",
            headquarters="Bengaluru",
            signals=[
                CompanySignalItem(
                    signal_type="funding_expansion",
                    headline="NeuroVector AI secures $10M seed round for database engine expansion",
                    evidence_url="https://techcrunch.com/neurovector"
                )
            ],
            source_name="Exa Semantic Discovery",
            source_provider="exa",
            source_url="https://neurovector.io",
            confidence=0.90
        )
    ]

    with patch("app.services.opportunity_orchestrator.provider_registry.get_configured_providers") as mock_conf, \
         patch("app.services.company_research_service.CompanyResearchService.research_company_classification_async", new_callable=AsyncMock) as mock_res:
        mock_res.return_value = {"classification": "startup", "size_range": "50-200", "evidence_excerpt": "AI company"}
        # Create mock provider returning above data
        mock_p1 = AsyncMock()
        mock_p1.provider_name = "tavily"
        mock_p1.search_jobs = AsyncMock(return_value=mock_jobs)
        mock_p1.search_companies = AsyncMock(return_value=[])

        mock_p2 = AsyncMock()
        mock_p2.provider_name = "exa"
        mock_p2.search_jobs = AsyncMock(return_value=[])
        mock_p2.search_companies = AsyncMock(return_value=mock_comps)

        mock_conf.return_value = [mock_p1, mock_p2]

        # Trigger Discovery Run
        disco_res = client.post(
            "/opportunities/discovery",
            json={
                "target_roles": ["Backend Engineer"],
                "limit": 10
            },
            headers=headers
        )
        assert disco_res.status_code == 202
        run_data = disco_res.json()
        assert "id" in run_data
        run_id = run_data["id"]

    # 4. Check Discovery Run Status
    status_res = client.get(f"/opportunities/discovery/{run_id}", headers=headers)
    assert status_res.status_code == 200

    # 5. List Opportunities
    list_res = client.get("/opportunities", headers=headers)
    assert list_res.status_code == 200
    opps = list_res.json()
    assert len(opps) >= 2  # 1 Advertised + 1 Emerging

    # Find the advertised opportunity
    adv_opp = next((o for o in opps if o["opportunity_type"] == "ADVERTISED"), None)
    assert adv_opp is not None
    assert adv_opp["job"] is not None
    assert adv_opp["job"]["company_name"] == "Zomato Labs"
    assert adv_opp["match_score"] >= 0.70
    assert adv_opp["recommended_action"] == "CONTACT_NOW"
    assert len(adv_opp["evidence_items"]) >= 1

    # Find the emerging unadvertised company opportunity
    emerging_opp = next((o for o in opps if o["opportunity_type"] == "EMERGING"), None)
    assert emerging_opp is not None
    assert emerging_opp["company"] is not None
    assert "NeuroVector" in emerging_opp["company"]["name"]
    assert emerging_opp["company"]["growth_signal_score"] >= 0.50

    # 6. Test Single Opportunity Details endpoint
    detail_res = client.get(f"/opportunities/{adv_opp['id']}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == adv_opp["id"]

    # 7. Test Status Update (Save opportunity)
    patch_res = client.patch(
        f"/opportunities/{adv_opp['id']}",
        json={"status": "SAVED"},
        headers=headers
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "SAVED"

    # Filter by SAVED
    saved_list = client.get("/opportunities?status=SAVED", headers=headers)
    assert len(saved_list.json()) == 1
    assert saved_list.json()[0]["id"] == adv_opp["id"]

    # 8. Test Company List and Detail endpoints
    companies_res = client.get("/opportunities/companies/all", headers=headers)
    assert companies_res.status_code == 200
    companies = companies_res.json()
    assert len(companies) >= 1
    
    comp_detail_res = client.get(f"/opportunities/companies/{companies[0]['id']}", headers=headers)
    assert comp_detail_res.status_code == 200
    assert comp_detail_res.json()["name"] == companies[0]["name"]

    # 9. Test Agent Run History / Audit Trail endpoint
    runs_res = client.get("/opportunities/runs", headers=headers)
    assert runs_res.status_code == 200
    runs = runs_res.json()
    assert len(runs) >= 1
    assert runs[0]["id"] == run_id
    assert runs[0]["run_type"] == "opportunity_discovery"


def test_multi_location_and_canonical_location_filtering(client):
    reg = client.post(
        "/auth/register",
        json={"email": "location.tester@example.com", "password": "Password123!", "full_name": "Location Tester"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.put(
        "/profile",
        json={
            "headline": "Lead Full Stack Engineer",
            "preferences": {
                "desired_roles": ["Software Engineer"],
                "preferred_locations": ["Mohali", "Noida", "Bengaluru"]
            },
            "skills": [
                {"name": "Python", "category": "technical", "status": "VERIFIED", "source": "USER_INPUT", "confidence_score": 1.0}
            ]
        },
        headers=headers
    )

    mock_jobs = [
        NormalizedJob(
            title="Software Engineer - Greater Noida",
            company_name="GN Innovations",
            description="Software engineer role based strictly in Greater Noida office.",
            location="Greater Noida",
            is_remote=False,
            work_arrangement="onsite",
            employment_type="full-time",
            primary_url="https://gninnovations.com/careers/se",
            source_name="Company Career Page",
            source_provider="tavily",
            extracted_skills=["Python"],
            confidence=0.95
        ),
        NormalizedJob(
            title="Software Engineer - Noida",
            company_name="Noida Cloud Systems",
            description="Software engineer in Noida Sector 62 campus.",
            location="Noida",
            is_remote=False,
            work_arrangement="onsite",
            employment_type="full-time",
            primary_url="https://noidacloud.com/careers/se",
            source_name="Company Career Page",
            source_provider="tavily",
            extracted_skills=["Python"],
            confidence=0.95
        ),
        NormalizedJob(
            title="Software Engineer - New Delhi",
            company_name="ND Tech Hub",
            description="Software engineer located at Connaught Place, New Delhi.",
            location="New Delhi",
            is_remote=False,
            work_arrangement="onsite",
            employment_type="full-time",
            primary_url="https://ndtech.com/careers/se",
            source_name="Company Career Page",
            source_provider="tavily",
            extracted_skills=["Python"],
            confidence=0.95
        ),
        NormalizedJob(
            title="Software Engineer - Delhi",
            company_name="Old Delhi Ventures",
            description="Software engineer in North Delhi hub.",
            location="Delhi",
            is_remote=False,
            work_arrangement="onsite",
            employment_type="full-time",
            primary_url="https://delhiventures.com/careers/se",
            source_name="Company Career Page",
            source_provider="tavily",
            extracted_skills=["Python"],
            confidence=0.95
        ),
        NormalizedJob(
            title="Software Engineer - Mohali Campus",
            company_name="Mohali Global Corp",
            description="Software engineer located in Mohali IT Park.",
            location="Mohali",
            is_remote=False,
            work_arrangement="onsite",
            employment_type="full-time",
            primary_url="https://mohalicorp.com/careers/se",
            source_name="Company Career Page",
            source_provider="tavily",
            extracted_skills=["Python"],
            confidence=0.95
        ),
    ]

    with patch("app.services.opportunity_orchestrator.provider_registry.get_configured_providers") as mock_conf, \
         patch("app.services.company_research_service.CompanyResearchService.research_company_classification_async", new_callable=AsyncMock) as mock_res:
        mock_res.return_value = {"classification": "startup", "size_range": "50-200", "evidence_excerpt": "AI company"}
        mock_p = AsyncMock()
        mock_p.provider_name = "tavily"
        mock_p.search_jobs = AsyncMock(return_value=mock_jobs)
        mock_p.search_companies = AsyncMock(return_value=[])
        mock_conf.return_value = [mock_p]

        # Trigger multi-location discovery run
        disco_res = client.post(
            "/opportunities/discovery",
            json={
                "target_roles": ["Software Engineer"],
                "locations": ["Noida", "Greater Noida", "Mohali"],
                "work_arrangement": "onsite",
                "employment_type": "full-time",
                "experience_level": "mid",
                "limit": 20
            },
            headers=headers
        )
        assert disco_res.status_code == 202
        disco_data = disco_res.json()
        assert "id" in disco_data

        # Check run status & query_params persistence
        run_status = client.get(f"/opportunities/discovery/{disco_data['id']}", headers=headers)
        assert run_status.status_code == 200
        qp = run_status.json()["query_params"]
        assert "Noida" in qp.get("locations", [])
        assert "Greater Noida" in qp.get("locations", [])
        assert qp.get("work_arrangement") == "onsite"
        assert qp.get("employment_type") == "full-time"

    # Verify canonical location filtering precision:
    # 1. Filter by Noida -> Should NOT match "Greater Noida"
    noida_res = client.get("/opportunities?location=Noida", headers=headers)
    assert noida_res.status_code == 200
    noida_opps = noida_res.json()
    assert len(noida_opps) >= 1
    for opp in noida_opps:
        loc = opp["job"]["location"] if opp["job"] else (opp["company"]["headquarters"] if opp["company"] else "")
        assert "greater noida" not in loc.lower(), f"Expected Noida but got Greater Noida: {loc}"
        assert "noida" in loc.lower()

    # 2. Filter by Greater Noida -> Should NOT match "Noida"
    gn_res = client.get("/opportunities?location=Greater%20Noida", headers=headers)
    assert gn_res.status_code == 200
    gn_opps = gn_res.json()
    assert len(gn_opps) >= 1
    for opp in gn_opps:
        loc = opp["job"]["location"] if opp["job"] else ""
        assert loc.lower() == "greater noida"

    # 3. Filter by Delhi -> Should NOT match "New Delhi"
    delhi_res = client.get("/opportunities?location=Delhi", headers=headers)
    assert delhi_res.status_code == 200
    delhi_opps = delhi_res.json()
    assert len(delhi_opps) >= 1
    for opp in delhi_opps:
        loc = opp["job"]["location"] if opp["job"] else ""
        assert "new delhi" not in loc.lower(), f"Expected Delhi but got New Delhi: {loc}"
        assert "delhi" in loc.lower()

    # 4. Filter by New Delhi -> Should NOT match plain "Delhi"
    nd_res = client.get("/opportunities?location=New%20Delhi", headers=headers)
    assert nd_res.status_code == 200
    nd_opps = nd_res.json()
    assert len(nd_opps) >= 1
    for opp in nd_opps:
        loc = opp["job"]["location"] if opp["job"] else ""
        assert loc.lower() == "new delhi"

    # 5. Filter by Mohali -> Only returns Mohali
    mohali_res = client.get("/opportunities?location=Mohali", headers=headers)
    assert mohali_res.status_code == 200
    mohali_opps = mohali_res.json()
    assert len(mohali_opps) >= 1
    for opp in mohali_opps:
        loc = opp["job"]["location"] if opp["job"] else ""
        assert "mohali" in loc.lower()


def test_filter_suggestions_endpoint(client):
    reg = client.post(
        "/auth/register",
        json={"email": "filter.tester@example.com", "password": "Password123!", "full_name": "Filter Tester"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/opportunities/filter-suggestions", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "locations" in data
    assert "skills" in data
    assert len(data["locations"]) > 0
    assert len(data["skills"]) > 0
    assert "Bengaluru" in data["locations"]
    assert "Python" in data["skills"]

    # Filter with q parameter
    res_q = client.get("/opportunities/filter-suggestions?q=Py", headers=headers)
    assert res_q.status_code == 200
    data_q = res_q.json()
    assert len(data_q["skills"]) > 0
    for s in data_q["skills"]:
        assert "py" in s.lower()


