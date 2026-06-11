# TechKraft Recruitment Dashboard

An internal candidate scoring and review dashboard for TechKraft's recruitment workflow. Built with FastAPI, React + Vite, SQLite, and Docker Compose.

---

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <your-repo-url>
cd techkraft

# 2. Set up environment
cp .env.example .env
# Edit .env and set a strong SECRET_KEY

# 3. Launch both services
docker compose up --build
```

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API docs**: http://localhost:8000/docs

### Demo Accounts (seeded automatically)

| Role     | Email                      | Password   |
|----------|----------------------------|------------|
| Admin    | admin@techkraft.com        | admin123   |
| Reviewer | reviewer@techkraft.com     | review123  |

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

---

## Example API Calls

```bash
# Login and capture token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@techkraft.com","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# List candidates with filters
curl "http://localhost:8000/candidates?status=new&limit=5" \
  -H "Authorization: Bearer $TOKEN"

# Get candidate detail
curl http://localhost:8000/candidates/<id> \
  -H "Authorization: Bearer $TOKEN"

# Submit a score
curl -X POST http://localhost:8000/candidates/<id>/scores \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category":"Technical","score":4,"note":"Strong fundamentals"}'

# Trigger AI summary (2s mock delay)
curl -X POST http://localhost:8000/candidates/<id>/summary \
  -H "Authorization: Bearer $TOKEN"

# Register a new reviewer (role is always hardcoded to reviewer)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@example.com","password":"secure123"}'
```

---

## Debugging Signal — Bug Identification

The following snippet from the assignment has a critical performance bug:

```python
def search_candidates(status: str, keyword: str, page: int, page_size: int):
    all_candidates = db.execute("SELECT * FROM candidates").fetchall()
    filtered = [c for c in all_candidates if c["status"] == status]
    # ... also filter by keyword in Python ...
    offset = (page - 1) * page_size
    return filtered[offset : offset + page_size]
```

**The bug:** `SELECT * FROM candidates` fetches every row in the table into application memory, then filters in Python. This is an unbounded full-table scan.

**Why it matters at scale:** With 10,000 candidates this loads ~10MB+ into memory on every request. With 100 concurrent users that becomes gigabytes of redundant data transfer and Python-side processing. It also defeats database indexes entirely — the index on `status` is never used, because all rows are fetched before any filtering occurs. Pagination is applied to the already-filtered Python list, so the query cost is always O(total rows) regardless of page size.

**The correct approach:** Push all filtering and pagination into SQL:

```python
def search_candidates(status: str, keyword: str, page: int, page_size: int):
    offset = (page - 1) * page_size
    query = """
        SELECT * FROM candidates
        WHERE status = :status
          AND (name ILIKE :kw OR email ILIKE :kw OR role_applied ILIKE :kw)
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """
    return db.execute(query, {
        "status": status,
        "kw": f"%{keyword}%",
        "limit": page_size,
        "offset": offset,
    }).fetchall()
```

This lets the database use its indexes, transfers only the rows the client actually needs, and scales to millions of rows with constant query cost per page.

This project implements the correct pattern throughout `candidate_service.py` using SQLAlchemy's query builder with `.where()`, `.limit()`, and `.offset()` clauses, plus a separate `COUNT(*)` query scoped to the same filters for accurate pagination totals.

---

## Architecture Decision Records

### ADR 1: SQLite over DynamoDB for local development

**Context:** The assignment mentioned "DynamoDB-style or SQLite." DynamoDB requires AWS credentials and a local emulator (DynamoDB Local via Docker), adding friction to setup.

**Decision:** Use SQLite with SQLAlchemy's async driver (`aiosqlite`). The schema uses explicit indexes on `candidates.status`, `candidates.role_applied`, and `scores.candidate_id` — the same access patterns DynamoDB would model with GSIs.

**Trade-off:** SQLite is single-writer and not horizontally scalable. For production at TechKraft's scale a PostgreSQL swap would be one connection string change (`asyncpg` driver), since SQLAlchemy abstracts the dialect. DynamoDB would require rewriting the query layer entirely.

---

### ADR 2: JWT Bearer tokens over session cookies

**Context:** The frontend and backend run on separate ports (5173 / 8000), making same-site cookies awkward without a reverse proxy. The API also needs to be callable from `curl` and future mobile clients.

**Decision:** Issue signed JWTs (8-hour expiry) via the `python-jose` library. The role (`admin` / `reviewer`) is embedded in the token payload so authorization checks are stateless — no DB round-trip per request.

**Trade-off:** JWTs can't be revoked before expiry without a token blocklist (adds statefulness). For an internal tool with an 8-hour window this is acceptable. The role is read from the database on every authenticated request (`get_current_user`) rather than trusted from the token payload, so a role change takes effect immediately.

---

### ADR 3: Skills stored as JSON text in SQLite

**Context:** SQLite has no native array type. Options were: a separate `candidate_skills` join table, a JSON column (SQLite 3.38+ supports `json_each`), or serialized text.

**Decision:** Store skills as a JSON array in a `TEXT` column (e.g. `'["React","Python"]'`). Filtering uses `ILIKE '%"React"%'` which is fast enough for this dataset size.

**Trade-off:** The LIKE-based skill filter has false positive risk on partial matches (e.g. searching "Java" would match "JavaScript"). For a production system the join table approach is cleaner and supports exact-match indexed lookups. The JSON approach was chosen to keep the schema flat and the service layer simple within the time constraint.

---

## Learning Reflection

I used the async SQLAlchemy 2.0 style (`async_sessionmaker`, `await session.execute(...)`) for the first time here — the transition from synchronous SQLAlchemy requires careful thinking about session lifecycles, especially ensuring `await session.flush()` is called before reading auto-generated IDs back. Given more time, I'd explore adding a real-time score feed using the SSE endpoint on the detail page and investigate replacing the mock AI summary with a genuine LLM call via the Anthropic API, streaming the response token-by-token to the frontend for a better perceived latency experience.

---

## Project Structure

```
/
├── README.md
├── docker-compose.yml
├── .env.example          # Safe template — never commit .env
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py       # FastAPI app, lifespan, CORS, seed data
│   │   ├── models.py     # SQLAlchemy ORM models
│   │   ├── schemas.py    # Pydantic request/response schemas
│   │   ├── auth.py       # JWT creation, password hashing, dependencies
│   │   ├── database.py   # Async engine, session factory, init_db
│   │   ├── routers/
│   │   │   ├── auth.py        # /auth/register, /auth/login, /auth/me
│   │   │   └── candidates.py  # /candidates + /scores + /summary + /stream
│   │   └── services/
│   │       └── candidate_service.py  # Business logic, all DB queries
│   └── tests/
│       └── test_api.py   # 5 async tests covering auth + RBAC + CRUD
└── frontend/
    ├── Dockerfile
    ├── index.html
    ├── package.json
    ├── vite.config.js    # Dev proxy: /api → http://backend:8000
    └── src/
        ├── main.jsx
        ├── App.jsx              # Routes + AuthProvider
        ├── index.css            # Full design system
        ├── api/
        │   └── client.js        # Fetch wrapper, token handling
        ├── components/
        │   └── AuthContext.jsx  # Auth state, login/logout
        └── pages/
            ├── LoginPage.jsx          # Login form + demo account shortcuts
            ├── CandidatesPage.jsx     # List + filters + pagination + add modal
            └── CandidateDetailPage.jsx # Detail + scoring + AI summary + admin notes
```

---

## Role Access Summary

| Feature                        | Reviewer         | Admin     |
|-------------------------------|------------------|-----------|
| View candidate list           | ✅               | ✅        |
| View candidate detail         | ✅               | ✅        |
| View own scores               | ✅               | ✅        |
| View all reviewers' scores    | ❌               | ✅        |
| View internal notes           | ❌               | ✅        |
| Edit internal notes           | ❌               | ✅        |
| Submit scores                 | ✅               | ✅        |
| Trigger AI summary            | ✅               | ✅        |
| Add / archive candidates      | ❌               | ✅        |
| Change candidate status       | ❌               | ✅        |
| Register role at signup       | always reviewer  | N/A       |
