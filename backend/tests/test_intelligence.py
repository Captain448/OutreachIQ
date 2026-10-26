import fitz
import io


def test_profile_intelligence_synthesis(client):
    reg = client.post(
        "/auth/register",
        json={"email": "marcus.ai@example.com", "password": "Password123!", "full_name": "Marcus Vance"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Add profile with explicit React skill and preferences
    client.put(
        "/profile",
        json={
            "headline": "Full-Stack AI Developer",
            "preferences": {
                "desired_roles": ["Frontend Engineer", "Full Stack Developer"],
                "preferred_industries": ["Enterprise AI"],
                "remote_preference": "remote"
            },
            "skills": [
                {
                    "name": "React",
                    "category": "frameworks",
                    "status": "VERIFIED",
                    "source": "USER_INPUT",
                    "evidence": "4 years production experience building React dashboards",
                    "confidence_score": 1.0
                }
            ]
        },
        headers=headers
    )

    # Upload resume with Python and FastAPI
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Marcus Vance - Python & FastAPI Developer", fontsize=12)
    page.insert_text((50, 80), "Skills: Python, FastAPI, Docker, PostgreSQL", fontsize=10)
    pdf_buf = io.BytesIO()
    doc.save(pdf_buf)
    doc.close()

    client.post(
        "/resumes",
        data={"title": "Backend Focus", "target_role": "Backend Developer"},
        files={"file": ("marcus_backend.pdf", pdf_buf.getvalue(), "application/pdf")},
        headers=headers
    )

    # Fetch candidate intelligence representation
    intel_res = client.get("/profile/intelligence", headers=headers)
    assert intel_res.status_code == 200
    data = intel_res.json()

    # Verify identity
    assert data["identity"]["full_name"] == "Marcus Vance"
    assert data["identity"]["email"] == "marcus.ai@example.com"

    # Verify skills segregation
    verified_names = {s["name"].lower() for s in data["verified_skills"]}
    assert "react" in verified_names
    assert "python" in verified_names
    assert "fastapi" in verified_names
    assert "docker" in verified_names

    # Check evidence-grounded inference (React -> JavaScript inference)
    inferred_names = {s["name"].lower() for s in data["inferred_skills"]}
    assert "javascript" in inferred_names

    # Verify resume inventory
    assert len(data["resume_inventory"]) == 1
    assert data["resume_inventory"][0]["title"] == "Backend Focus"

    # Verify career directions
    directions = [cd["target_role"] for cd in data["career_directions"]]
    assert "Backend Developer" in directions
    assert "Frontend Engineer" in directions

    # Verify grounded explanation
    assert len(data["evidence_grounding_summary"]) > 20
    assert data["profile_completeness"]["overall_percentage"] > 0
