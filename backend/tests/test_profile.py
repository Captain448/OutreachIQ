def test_profile_lifecycle(client):
    # Register user
    reg = client.post(
        "/auth/register",
        json={
            "email": "sarah.dev@example.com",
            "password": "Password12345!",
            "full_name": "Sarah Developer"
        }
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Initial profile fetch
    get_res = client.get("/profile", headers=headers)
    assert get_res.status_code == 200
    pdata = get_res.json()
    assert pdata["full_name"] == "Sarah Developer"
    assert pdata["email"] == "sarah.dev@example.com"
    assert pdata["completeness_score"] >= 0

    # Update profile with comprehensive details
    update_payload = {
        "full_name": "Sarah Connor Developer",
        "headline": "Lead Systems Architect & Distributed Systems Engineer",
        "phone": "+1-555-0199",
        "location": "Seattle, WA",
        "bio": "Passionate systems engineer building resilient distributed infrastructure and AI data pipelines.",
        "links": {
            "linkedin": "https://linkedin.com/in/sarah-connor",
            "github": "https://github.com/sarahconnor",
            "portfolio": "https://sarahconnor.tech"
        },
        "education": [
            {
                "institution": "University of Washington",
                "degree": "B.S. Computer Science",
                "field_of_study": "Systems & Networking",
                "start_year": 2018,
                "graduation_year": 2022,
                "grade_or_gpa": "3.9",
                "details": "Focus on concurrent algorithms and operating systems."
            }
        ],
        "work_experience": [
            {
                "company": "CloudScale Systems",
                "role": "Senior Backend Engineer",
                "location": "Seattle, WA (Hybrid)",
                "start_date": "2022-06",
                "end_date": "Present",
                "is_current": True,
                "description": "Architected low-latency message streaming queues handling 100k msg/sec.",
                "technologies": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes"]
            }
        ],
        "projects": [
            {
                "title": "StreamMesh Engine",
                "description": "Distributed pub-sub broker written in Python and Go.",
                "technologies": ["Python", "Go", "Docker"],
                "role_contribution": "Designed core consensus protocol and peer discovery.",
                "github_url": "https://github.com/sarahconnor/streammesh"
            }
        ],
        "skills": [
            {
                "name": "Python",
                "category": "programming_languages",
                "status": "VERIFIED",
                "source": "USER_INPUT",
                "evidence": "Primary backend language used across all production systems",
                "confidence_score": 1.0
            },
            {
                "name": "FastAPI",
                "category": "frameworks",
                "status": "VERIFIED",
                "source": "USER_INPUT",
                "confidence_score": 1.0
            }
        ],
        "preferences": {
            "desired_roles": ["Distributed Systems Engineer", "Backend Staff Architect"],
            "preferred_industries": ["Cloud Infrastructure", "FinTech", "AI Platforms"],
            "preferred_locations": ["Seattle, WA", "Remote"],
            "remote_preference": "hybrid",
            "experience_level": "senior",
            "employment_preference": "full-time"
        }
    }

    put_res = client.put("/profile", json=update_payload, headers=headers)
    assert put_res.status_code == 200
    updated_data = put_res.json()
    assert updated_data["headline"] == "Lead Systems Architect & Distributed Systems Engineer"
    assert updated_data["full_name"] == "Sarah Connor Developer"
    assert len(updated_data["education"]) == 1
    assert len(updated_data["work_experience"]) == 1
    assert len(updated_data["projects"]) == 1
    assert len(updated_data["skills"]) == 2
    assert updated_data["preferences"]["remote_preference"] == "hybrid"
    assert updated_data["completeness_score"] > 80


def test_profile_custom_links_persistence(client):
    # Register candidate
    reg = client.post(
        "/auth/register",
        json={
            "email": "custom.links@example.com",
            "password": "Password12345!",
            "full_name": "Alex Custom"
        }
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update with standard links and dynamic custom links array
    custom_links_payload = [
        {"label": "LeetCode", "url": "https://leetcode.com/u/alexcustom"},
        {"label": "Google Scholar", "url": "https://scholar.google.com/citations?user=12345"},
        {"label": "Substack", "url": "https://alexcustom.substack.com"}
    ]
    payload = {
        "headline": "Full Stack Engineer",
        "links": {
            "linkedin": "https://linkedin.com/in/alexcustom",
            "github": "https://github.com/alexcustom",
            "portfolio": "https://alexcustom.dev",
            "custom_links": custom_links_payload
        }
    }

    put_res = client.put("/profile", json=payload, headers=headers)
    assert put_res.status_code == 200
    data = put_res.json()
    assert data["links"]["linkedin"] == "https://linkedin.com/in/alexcustom"
    assert data["links"]["github"] == "https://github.com/alexcustom"
    assert data["links"]["portfolio"] == "https://alexcustom.dev"
    assert len(data["links"]["custom_links"]) == 3
    assert data["links"]["custom_links"][0]["label"] == "LeetCode"
    assert data["links"]["custom_links"][0]["url"] == "https://leetcode.com/u/alexcustom"
    assert data["links"]["custom_links"][1]["label"] == "Google Scholar"
    assert data["links"]["custom_links"][2]["label"] == "Substack"

    # GET /profile to ensure clean persistence round-trip
    get_res = client.get("/profile", headers=headers)
    assert get_res.status_code == 200
    persisted = get_res.json()
    assert persisted["links"]["custom_links"] == custom_links_payload
