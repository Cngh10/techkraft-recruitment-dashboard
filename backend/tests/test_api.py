import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Override DB before importing app
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = "test-secret-key"

from app.main import app
from app.database import get_db, init_db
from app.models import Base

test_engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def admin_token(client):
    # Register then promote via DB
    reg = await client.post("/auth/register", json={
        "email": "admin@test.com", "password": "admin123"
    })
    user_id = reg.json()["id"]
    # Manually set role to admin
    async with TestSessionLocal() as session:
        from app.models import User
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.role = "admin"
        await session.commit()
    login = await client.post("/auth/login", json={
        "email": "admin@test.com", "password": "admin123"
    })
    return login.json()["access_token"]


@pytest_asyncio.fixture
async def reviewer_token(client):
    await client.post("/auth/register", json={
        "email": "reviewer@test.com", "password": "review123"
    })
    login = await client.post("/auth/login", json={
        "email": "reviewer@test.com", "password": "review123"
    })
    return login.json()["access_token"]


@pytest_asyncio.fixture
async def reviewer2_token(client):
    await client.post("/auth/register", json={
        "email": "reviewer2@test.com", "password": "review123"
    })
    login = await client.post("/auth/login", json={
        "email": "reviewer2@test.com", "password": "review123"
    })
    return login.json()["access_token"]


# ── Test 1: Create a candidate (admin only) and verify response ────────────────

@pytest.mark.asyncio
async def test_create_candidate(client, admin_token):
    payload = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "role_applied": "Full Stack Engineer",
        "skills": ["Python", "React"],
    }
    resp = await client.post(
        "/candidates",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Jane Doe"
    assert data["email"] == "jane@example.com"
    assert data["status"] == "new"
    assert "Python" in data["skills"]
    assert "id" in data


# ── Test 2: Auth enforcement — reviewer cannot see another reviewer's scores ──

@pytest.mark.asyncio
async def test_reviewer_cannot_see_other_reviewer_scores(
    client, admin_token, reviewer_token, reviewer2_token
):
    # Admin creates a candidate
    cand_resp = await client.post(
        "/candidates",
        json={"name": "Test Cand", "email": "cand@test.com", "role_applied": "Engineer", "skills": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    cand_id = cand_resp.json()["id"]

    # Reviewer 1 submits a score
    await client.post(
        f"/candidates/{cand_id}/scores",
        json={"category": "Technical", "score": 4, "note": "Good"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )

    # Reviewer 2 fetches the candidate — should see 0 scores (not reviewer1's)
    resp = await client.get(
        f"/candidates/{cand_id}",
        headers={"Authorization": f"Bearer {reviewer2_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["scores"] == []


# ── Test 3: Registration always assigns reviewer role (never from client) ─────

@pytest.mark.asyncio
async def test_registration_role_always_reviewer(client):
    resp = await client.post("/auth/register", json={
        "email": "hacker@test.com",
        "password": "password123",
    })
    assert resp.status_code == 201
    assert resp.json()["role"] == "reviewer"


# ── Test 4: Reviewer cannot access internal_notes ─────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_cannot_see_internal_notes(client, admin_token, reviewer_token):
    cand_resp = await client.post(
        "/candidates",
        json={
            "name": "Private Cand",
            "email": "private@test.com",
            "role_applied": "Engineer",
            "skills": [],
            "internal_notes": "SECRET ADMIN NOTE",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    cand_id = cand_resp.json()["id"]

    resp = await client.get(
        f"/candidates/{cand_id}",
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["internal_notes"] is None


# ── Test 5: Admin CAN see internal_notes ──────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_see_internal_notes(client, admin_token):
    cand_resp = await client.post(
        "/candidates",
        json={
            "name": "Admin Cand",
            "email": "admincand@test.com",
            "role_applied": "Engineer",
            "skills": [],
            "internal_notes": "VERY IMPORTANT NOTE",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    cand_id = cand_resp.json()["id"]

    resp = await client.get(
        f"/candidates/{cand_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["internal_notes"] == "VERY IMPORTANT NOTE"
