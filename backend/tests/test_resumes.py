import io
import fitz
import docx
from app.models.resume import ParsingStatus


def create_test_pdf(text_lines: list[str]) -> io.BytesIO:
    doc = fitz.open()
    page = doc.new_page()
    y = 50
    for line in text_lines:
        page.insert_text((50, y), line, fontsize=11)
        y += 20
    pdf_bytes = io.BytesIO()
    doc.save(pdf_bytes)
    doc.close()
    pdf_bytes.seek(0)
    return pdf_bytes


def create_test_docx(text_lines: list[str]) -> io.BytesIO:
    doc = docx.Document()
    for line in text_lines:
        doc.add_paragraph(line)
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    return docx_bytes


def test_resume_upload_and_parsing(client):
    # Register user
    reg = client.post(
        "/auth/register",
        json={"email": "jordan.eng@example.com", "password": "Password123!", "full_name": "Jordan Eng"}
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Test PDF upload & parsing
    pdf_lines = [
        "Jordan Eng - Senior Software Engineer",
        "Email: jordan.eng@example.com Phone: 555-123-4567",
        "Experience:",
        "- Built microservices using Python, FastAPI, Docker, and PostgreSQL.",
        "Skills:",
        "Python, FastAPI, TypeScript, React, Docker, Kubernetes, PostgreSQL, Git",
        "Education:",
        "Bachelor of Science in Computer Engineering from Stanford University, 2021."
    ]
    pdf_buffer = create_test_pdf(pdf_lines)
    
    upload_res = client.post(
        "/resumes",
        data={"title": "Backend Engineering Resume", "target_role": "Backend Engineer"},
        files={"file": ("resume_backend.pdf", pdf_buffer.getvalue(), "application/pdf")},
        headers=headers
    )
    assert upload_res.status_code == 201
    pdf_data = upload_res.json()
    assert pdf_data["title"] == "Backend Engineering Resume"
    assert pdf_data["target_role"] == "Backend Engineer"
    assert pdf_data["is_preferred"] is True  # First resume auto-preferred
    assert pdf_data["parsing_status"] == ParsingStatus.PARSED
    assert pdf_data["parsing_confidence"] >= 0.90
    assert len(pdf_data["extracted_skills"]) >= 5
    skill_names = [s["name"].lower() for s in pdf_data["extracted_skills"]]
    assert "python" in skill_names
    assert "fastapi" in skill_names
    assert "docker" in skill_names

    # 2. Test second resume upload (DOCX format)
    docx_lines = [
        "Jordan Eng - AI & ML Specialist",
        "Email: jordan.eng@example.com",
        "Skills:",
        "PyTorch, Machine Learning, Deep Learning, Python, LangChain, NLP",
        "Projects:",
        "- Built RAG agent with PyTorch and LangChain."
    ]
    docx_buffer = create_test_docx(docx_lines)
    upload_res2 = client.post(
        "/resumes",
        data={"title": "AI/ML Focused Resume", "target_role": "AI/ML Engineer", "is_preferred": "true"},
        files={"file": ("resume_aiml.docx", docx_buffer.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=headers
    )
    assert upload_res2.status_code == 201
    docx_data = upload_res2.json()
    assert docx_data["title"] == "AI/ML Focused Resume"
    assert docx_data["target_role"] == "AI/ML Engineer"
    assert docx_data["is_preferred"] is True

    # Check that previous resume is no longer preferred
    list_res = client.get("/resumes", headers=headers)
    assert list_res.status_code == 200
    resumes_list = list_res.json()
    assert len(resumes_list) == 2
    preferred_resumes = [r for r in resumes_list if r["is_preferred"]]
    assert len(preferred_resumes) == 1
    assert preferred_resumes[0]["id"] == docx_data["id"]

    # 3. Test update / rename resume
    update_res = client.put(
        f"/resumes/{docx_data['id']}",
        json={"title": "Senior AI Research Engineer Resume"},
        headers=headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Senior AI Research Engineer Resume"

    # 4. Test delete resume
    del_res = client.delete(f"/resumes/{docx_data['id']}", headers=headers)
    assert del_res.status_code == 204

    # Verify only 1 resume remains
    list_res2 = client.get("/resumes", headers=headers)
    assert len(list_res2.json()) == 1


def test_invalid_resume_files(client):
    reg = client.post(
        "/auth/register",
        json={"email": "bad.file@example.com", "password": "Password123!", "full_name": "Test User"}
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Unsupported file extension (.exe or .txt)
    txt_content = b"This is a plain text file, not a PDF or DOCX"
    bad_ext_res = client.post(
        "/resumes",
        data={"title": "Text file resume"},
        files={"file": ("resume.txt", txt_content, "text/plain")},
        headers=headers
    )
    assert bad_ext_res.status_code == 400
    assert "Unsupported file format" in bad_ext_res.json()["detail"]

    # Empty PDF file
    empty_res = client.post(
        "/resumes",
        data={"title": "Empty PDF"},
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=headers
    )
    assert empty_res.status_code == 400


def test_get_resumes_returns_direct_array_and_requires_auth(client):
    # 1. Unauthenticated request should fail with 401
    unauth_res = client.get("/resumes")
    assert unauth_res.status_code == 401

    # 2. Register a new user
    reg = client.post(
        "/auth/register",
        json={"email": "array.test@example.com", "password": "Password123!", "full_name": "Array Tester"}
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Before any uploads, should return an empty direct JSON array
    empty_list_res = client.get("/resumes", headers=headers)
    assert empty_list_res.status_code == 200
    empty_data = empty_list_res.json()
    assert isinstance(empty_data, list)
    assert len(empty_data) == 0

    # 4. Upload a resume
    pdf_lines = [
        "Array Tester - Software Engineer",
        "Skills: Python, TypeScript, SQL",
        "Experience: Built APIs and web apps."
    ]
    pdf_buffer = create_test_pdf(pdf_lines)
    upload_res = client.post(
        "/resumes",
        data={"title": "Array Test Resume", "target_role": "Full Stack Engineer"},
        files={"file": ("tester_resume.pdf", pdf_buffer.getvalue(), "application/pdf")},
        headers=headers
    )
    assert upload_res.status_code == 201

    # 5. Verify GET /resumes returns a direct JSON array of resume objects
    list_res = client.get("/resumes", headers=headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert isinstance(data, list)
    assert len(data) == 1
    resume = data[0]
    assert isinstance(resume, dict)
    assert "id" in resume
    assert resume["title"] == "Array Test Resume"
    assert resume["original_filename"] == "tester_resume.pdf"
    assert "parsing_status" in resume
    assert "is_preferred" in resume
    assert resume["is_preferred"] is True
    assert isinstance(resume["extracted_skills"], list)

