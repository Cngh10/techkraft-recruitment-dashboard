from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import json

from .database import init_db, AsyncSessionLocal
from .routers import auth as auth_router, candidates as candidates_router
from .models import User, Candidate, Score
from .auth import hash_password
from sqlalchemy import select


async def seed_data():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        if result.scalars().first():
            return

        admin = User(email="admin@techkraft.com", hashed_password=hash_password("admin123"), role="admin")
        reviewer = User(email="reviewer@techkraft.com", hashed_password=hash_password("review123"), role="reviewer")
        db.add_all([admin, reviewer])
        await db.flush()

        seed_candidates = [
            ("Alice Chen",     "alice@example.com",  "Full Stack Engineer",   "new",
             ["React", "Python", "FastAPI", "PostgreSQL", "Docker"],
             None),
            ("Bob Martinez",   "bob@example.com",    "Backend Engineer",      "reviewed",
             ["Go", "Kubernetes", "Redis", "gRPC", "Terraform"],
             "Strong system design instincts. Hesitant on frontend exposure."),
            ("Carol Nguyen",   "carol@example.com",  "Frontend Engineer",     "hired",
             ["TypeScript", "Vue", "Figma", "CSS", "Testing"],
             "Exceptional craft. Offered senior role. Start date confirmed."),
            ("David Kim",      "david@example.com",  "DevOps Engineer",       "rejected",
             ["Terraform", "AWS", "Docker", "CI/CD", "Ansible"],
             "Technically sound but cultural alignment concerns raised by panel."),
            ("Eva Patel",      "eva@example.com",    "Full Stack Engineer",   "new",
             ["Node.js", "React", "MongoDB", "GraphQL", "AWS"],
             None),
            ("Frank Liu",      "frank@example.com",  "Data Engineer",         "reviewed",
             ["Python", "Spark", "Airflow", "dbt", "Snowflake"],
             "Strong data platform background. Pipeline architecture question was weak."),
            ("Grace Okonkwo",  "grace@example.com",  "ML Engineer",           "new",
             ["Python", "PyTorch", "MLflow", "Kubernetes", "Rust"],
             None),
            ("Hassan Al-Rashid","hassan@example.com","Platform Engineer",     "reviewed",
             ["Rust", "gRPC", "Kafka", "eBPF", "Linux"],
             "Exceptional low-level systems knowledge. Compensation expectations high."),
        ]

        cand_objs = []
        for name, email, role, status, skills, notes in seed_candidates:
            c = Candidate(
                name=name, email=email, role_applied=role, status=status,
                skills=json.dumps(skills), internal_notes=notes,
            )
            db.add(c)
            cand_objs.append(c)

        await db.flush()

        # Seed some scores so reviewers can see something right away
        sample_scores = [
            (cand_objs[1], reviewer.id, "Technical", 4, "Solid Go experience; Redis depth impressive."),
            (cand_objs[1], reviewer.id, "Communication", 3, "Answers precise but terse."),
            (cand_objs[2], reviewer.id, "Technical", 5, "Best CSS/TS we've seen this quarter."),
            (cand_objs[2], reviewer.id, "Culture Fit", 5, "Immediately clicked with the team."),
            (cand_objs[5], reviewer.id, "Technical", 4, "dbt and Airflow expertise is real."),
            (cand_objs[7], reviewer.id, "Technical", 5, "eBPF knowledge is rare. Extremely impressive."),
            (cand_objs[7], reviewer.id, "Problem Solving", 4, "Methodical debugger. Good instincts."),
        ]
        for cand, rev_id, cat, score, note in sample_scores:
            db.add(Score(candidate_id=cand.id, category=cat, score=score, reviewer_id=rev_id, note=note))

        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_data()
    yield


app = FastAPI(
    title="TechKraft Recruitment Intelligence API",
    version="2.0.0",
    description="""
## TechKraft Recruitment Intelligence Platform

Internal candidate scoring and review system with AI-powered analysis.

### Authentication
All protected endpoints require a **Bearer JWT token**.

1. `POST /auth/register` — create a reviewer account
2. `POST /auth/login` — get your token
3. Click **Authorize** (🔒) and enter: `Bearer <your_token>`

### Demo credentials
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@techkraft.com | admin123 |
| Reviewer | reviewer@techkraft.com | review123 |

### Role Access
- **Reviewer**: Score candidates, view own scores, trigger AI summaries
- **Admin**: All reviewer actions + view/edit all scores, internal notes, create/archive candidates
""",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://frontend:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(candidates_router.router)


@app.get("/health", tags=["system"], summary="Health check")
async def health():
    """Returns service health status. No authentication required."""
    return {"status": "ok", "service": "TechKraft Recruitment Intelligence API", "version": "2.0.0"}
