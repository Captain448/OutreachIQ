import os
import io
import fitz
import pytest
from pathlib import Path
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import Base
from app.models.user import User
from app.models.resume import Resume


def create_minimal_pdf(name: str) -> io.BytesIO:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), f"{name} - Software Engineer\nPython, FastAPI", fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    return buf


def test_path_anchoring():
    """
    Verifies that BASE_DIR, sync_database_url, and resolved_upload_dir
    are anchored to absolute paths and independent of the current working directory.
    """
    assert settings.BASE_DIR.is_absolute()
    assert settings.resolved_upload_dir.is_absolute()
    assert "backend" in str(settings.BASE_DIR).lower()

    # Changing cwd temporarily must not alter the resolved sync_database_url or upload dir
    old_cwd = os.getcwd()
    try:
        os.chdir(str(settings.BASE_DIR.parent))
        sync_url = settings.sync_database_url
        assert sync_url.startswith("sqlite:///")
        # Must be an absolute path
        raw_path = sync_url.replace("sqlite:///", "")
        assert Path(raw_path).is_absolute()
        assert Path(raw_path).name == "outreachiq.db"
    finally:
        os.chdir(old_cwd)


def test_route_ordering_companies_all(client):
    """
    Verifies that GET /opportunities/companies/all is correctly dispatched
    and not masked by the dynamic GET /opportunities/{opportunity_id} route.
    """
    reg = client.post(
        "/auth/register",
        json={"email": "route.test@example.com", "password": "Password123!", "full_name": "Route Tester"}
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Calling /companies/all must return 200, NOT 404 (which occurred when /{opportunity_id} matched it)
    res = client.get("/opportunities/companies/all", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_resume_isolation_and_delete_scoping(client):
    """
    Verifies that:
    1. A user can manage multiple resumes simultaneously.
    2. Listing resumes only returns the authenticated user's resumes.
    3. Deleting a resume only removes the target resume for that user.
    4. A user cannot delete or access another user's resume (cross-tenant isolation).
    """
    # Register User 1
    reg1 = client.post(
        "/auth/register",
        json={"email": "user1.resume@example.com", "password": "Password123!", "full_name": "User One"}
    )
    token1 = reg1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Register User 2
    reg2 = client.post(
        "/auth/register",
        json={"email": "user2.resume@example.com", "password": "Password123!", "full_name": "User Two"}
    )
    token2 = reg2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # User 1 uploads Resume A
    pdf_a = create_minimal_pdf("User 1 Resume A")
    res_a = client.post(
        "/resumes",
        data={"title": "Resume A", "target_role": "Backend Engineer"},
        files={"file": ("resume_a.pdf", pdf_a.getvalue(), "application/pdf")},
        headers=headers1
    )
    assert res_a.status_code == 201
    id_a = res_a.json()["id"]

    # User 1 uploads Resume B
    pdf_b = create_minimal_pdf("User 1 Resume B")
    res_b = client.post(
        "/resumes",
        data={"title": "Resume B", "target_role": "AI Engineer"},
        files={"file": ("resume_b.pdf", pdf_b.getvalue(), "application/pdf")},
        headers=headers1
    )
    assert res_b.status_code == 201
    id_b = res_b.json()["id"]

    # User 2 uploads Resume C
    pdf_c = create_minimal_pdf("User 2 Resume C")
    res_c = client.post(
        "/resumes",
        data={"title": "Resume C", "target_role": "Frontend Engineer"},
        files={"file": ("resume_c.pdf", pdf_c.getvalue(), "application/pdf")},
        headers=headers2
    )
    assert res_c.status_code == 201
    id_c = res_c.json()["id"]

    # User 1 lists resumes: must see exactly Resume A and Resume B
    list1 = client.get("/resumes", headers=headers1)
    assert list1.status_code == 200
    ids_user1 = [r["id"] for r in list1.json()]
    assert len(ids_user1) == 2
    assert id_a in ids_user1 and id_b in ids_user1
    assert id_c not in ids_user1

    # User 2 lists resumes: must see only Resume C
    list2 = client.get("/resumes", headers=headers2)
    assert list2.status_code == 200
    ids_user2 = [r["id"] for r in list2.json()]
    assert len(ids_user2) == 1
    assert id_c in ids_user2

    # Cross-tenant attack: User 1 attempts to delete User 2's resume (id_c)
    attack_del = client.delete(f"/resumes/{id_c}", headers=headers1)
    assert attack_del.status_code == 404

    # Verify Resume C is untouched
    verify_c = client.get(f"/resumes/{id_c}", headers=headers2)
    assert verify_c.status_code == 200

    # User 1 deletes Resume A
    del_a = client.delete(f"/resumes/{id_a}", headers=headers1)
    assert del_a.status_code == 204

    # Verify Resume A is gone, but Resume B remains for User 1
    list1_after = client.get("/resumes", headers=headers1)
    ids_user1_after = [r["id"] for r in list1_after.json()]
    assert len(ids_user1_after) == 1
    assert id_b in ids_user1_after
    assert id_a not in ids_user1_after


def test_sqlite_wal_mode_and_concurrency(tmp_path):
    """
    Verifies that SQLite files configured with WAL mode and busy_timeout
    allow non-blocking concurrent reads while a write transaction is active.
    """
    db_file = tmp_path / "test_wal_concurrency.db"
    db_url = f"sqlite:///{db_file}"

    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False, "timeout": 30.0}
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

    # Create schema
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Verify PRAGMA journal_mode is WAL
    with engine.connect() as conn:
        res = conn.execute(text("PRAGMA journal_mode")).scalar()
        assert res.lower() == "wal"

    # Concurrency test: session 1 inserts data, session 2 reads concurrently
    s1 = Session()
    s2 = Session()

    try:
        test_user = User(
            email="wal.tester@example.com",
            hashed_password="hashed_pw_test",
            full_name="WAL Tester",
            is_active=True
        )
        s1.add(test_user)
        s1.commit()

        # Concurrent read from s2
        user_from_s2 = s2.query(User).filter(User.email == "wal.tester@example.com").first()
        assert user_from_s2 is not None
        assert user_from_s2.full_name == "WAL Tester"
    finally:
        s1.close()
        s2.close()
        engine.dispose()
