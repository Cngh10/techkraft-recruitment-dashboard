import json
import asyncio
import random
import hashlib
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from fastapi import HTTPException

from ..models import Candidate, Score, User
from ..schemas import CandidateCreate, CandidateUpdate, ScoreCreate


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize_skills(skills: List[str]) -> str:
    return json.dumps(skills)

def _deserialize_skills(raw: str) -> List[str]:
    try:
        return json.loads(raw)
    except Exception:
        return []

def _candidate_to_dict(candidate: Candidate) -> dict:
    d = {c.name: getattr(candidate, c.name) for c in candidate.__table__.columns}
    d["skills"] = _deserialize_skills(d.get("skills", "[]"))
    return d


# ── Mock AI summary generation ────────────────────────────────────────────────

MOCK_SUMMARY_TEMPLATES = {
    "Technical": [
        "{name}'s technical profile for the {role} position is genuinely compelling. "
        "Their hands-on experience with {skills_str} reflects a practitioner who doesn't just understand tools — they understand *why* those tools exist. "
        "The breadth across {skill1} and {skill2} suggests an engineer comfortable operating at multiple layers of the stack. "
        "Recommend a deep-dive technical interview focused on system design trade-offs and debugging under constraint.",

        "From a technical lens, {name} brings a rare combination of breadth and depth to the {role} role. "
        "Proficiency in {skills_str} signals strong engineering fundamentals. "
        "What stands out is the pairing of {skill1} with {skill2} — a combination that implies real-world delivery experience, not just theoretical knowledge. "
        "Suggest assigning a take-home challenge that mirrors production complexity before advancing to final rounds.",

        "Technical assessment of {name}: this candidate's {role} application is backed by solid skill evidence in {skills_str}. "
        "The {skill1} expertise is particularly relevant given current team needs. "
        "Risk flag: skill recency is unverified — recommend probing how recently {skill2} has been used in a production context. "
        "Overall technical signal: strong.",
    ],
    "Communication": [
        "Communication signals for {name} are worth examining carefully. "
        "Candidates applying for {role} positions often underestimate how much clarity of thought matters beyond code. "
        "Their background in {skills_str} suggests experience working across team boundaries where communication is load-bearing. "
        "Recommend a structured behavioral interview focusing on cross-functional conflict resolution and stakeholder alignment.",

        "{name}'s profile implies a communicator shaped by technical depth. "
        "Engineers who work with {skill1} and {skill2} regularly must translate complexity to non-technical stakeholders — a skill that's hard to fake. "
        "For the {role} role, this matters enormously. "
        "Evaluate written communication artifacts (PRs, design docs, async updates) if available before forming a final view.",

        "For a {role} candidate, communication competency is as important as technical skill. "
        "{name}'s background in {skills_str} suggests comfort in environments that demand precision. "
        "Structured communication (e.g. RFC writing, incident post-mortems) likely part of their toolkit. "
        "Probe for specific examples of simplifying a complex technical decision for a non-engineer audience.",
    ],
    "Problem Solving": [
        "Problem-solving capacity is the hardest signal to read from a CV — but {name}'s trajectory tells an interesting story. "
        "Working with {skills_str} in a {role} context requires continuous problem decomposition under ambiguity. "
        "The combination of {skill1} and {skill2} often indicates someone who has debugged hard, unfamiliar systems. "
        "Recommend a live debugging session or war-game scenario rather than standard LeetCode during the technical round.",

        "{name} presents as a systems thinker with practical problem-solving instincts. "
        "Their {role} background combined with {skills_str} expertise suggests experience with problems that don't have clean answers. "
        "Particularly note the {skill1} experience — this domain rewards persistent, iterative problem-solvers over those who rely on pattern matching. "
        "High potential signal here.",

        "Assessing {name}'s problem-solving for a {role} position: the skill set in {skills_str} implies experience navigating real production failures. "
        "Problem-solving in distributed or complex environments like {skill1} builds a specific kind of instinct that classroom learning can't replicate. "
        "Ask for a specific incident they owned end-to-end — how they diagnosed, communicated, and prevented recurrence.",
    ],
    "Culture Fit": [
        "Culture fit is the most misused term in hiring — but it matters. "
        "{name}'s background in {skills_str} for a {role} role suggests exposure to collaborative, high-ownership engineering cultures. "
        "The specific pairing of {skill1} and {skill2} tends to attract builders who care about craft, not just output. "
        "Worth probing: what kind of feedback culture do they thrive in? Do they prefer autonomy or high-coordination environments?",

        "{name}'s profile reflects someone shaped by technical depth and likely by team-oriented workflows. "
        "Engineers fluent in {skill1} typically have strong opinions about code quality, which can be both an asset and a friction point. "
        "For the {role} position, assess alignment with team norms around decision-making pace and ownership distribution. "
        "Culture fit isn't about sameness — it's about productive friction.",

        "For {name}, culture alignment for a {role} role hinges on understanding their working style beyond the technical. "
        "Their expertise in {skills_str} suggests a candidate who has navigated complex organizational dynamics. "
        "Probe for how they handle disagreement with technical leadership, and how they balance individual output with team progress. "
        "Values alignment check recommended.",
    ],
    "Leadership": [
        "Leadership potential in {name} may not be immediately obvious from a {role} title — but the signals are there. "
        "Mastery of {skills_str} at a production level implies they have influenced architectural decisions, reviewed others' work, or led incident responses. "
        "The {skill1} experience in particular tends to push engineers into informal technical leadership roles. "
        "Probe: have they ever driven a cross-team initiative or changed a team's technical direction?",

        "{name}'s path through {skills_str} for a {role} function suggests growing technical leadership capability. "
        "Candidates with {skill1} depth often become the de facto experts others defer to — which is informal leadership by another name. "
        "For a mid-senior hire, ask about a moment they had to make a high-stakes technical call with incomplete information. "
        "That answer will tell you more about leadership than any title.",

        "Leadership signals for {name}: technical leaders in {role} positions aren't always people managers, but they set direction. "
        "The {skills_str} toolkit implies someone who has operated at scale, which is where real leadership instincts develop. "
        "Evaluate whether {name} has mentored others, driven adoption of a new pattern, or resolved a technical disagreement diplomatically. "
        "High ceiling candidate if leadership behaviors are confirmed.",
    ],
    "default": [
        "{name} is applying for the {role} position with a skill set spanning {skills_str}. "
        "Initial profiling suggests a well-rounded candidate with clear strengths in {skill1}. "
        "Current application status is '{status}'. "
        "Recommend proceeding to structured interview rounds to validate technical depth and cultural alignment. "
        "Overall signal: promising.",

        "Profile summary for {name}: applying as {role} with demonstrated capability in {skills_str}. "
        "The intersection of {skill1} and {skill2} is particularly relevant to current team needs. "
        "Status: {status}. Next step recommendation: standardized technical screen followed by a panel interview with cross-functional stakeholders.",

        "Candidate {name} presents a credible profile for the {role} opening. "
        "Skills in {skills_str} cover core requirements. "
        "{skill1} experience deserves deeper validation — surface-level familiarity vs production ownership matters significantly here. "
        "Hiring confidence: moderate-to-high pending interview outcomes.",
    ]
}

def _summary_context(candidate: Candidate) -> dict:
    skills = _deserialize_skills(candidate.skills)
    return {
        "name": candidate.name,
        "role": candidate.role_applied,
        "status": candidate.status,
        "skills_str": ", ".join(skills) if skills else "a broad technical background",
        "skill1": skills[0] if skills else "their primary stack",
        "skill2": skills[1] if len(skills) > 1 else "complementary tools",
    }


def _pick_summary_template(candidate_id: str, category: str) -> str:
    seed = int(hashlib.md5(f"{candidate_id}-{category}".encode()).hexdigest(), 16) % 1000
    random.seed(seed)
    templates = MOCK_SUMMARY_TEMPLATES.get(category, MOCK_SUMMARY_TEMPLATES["default"])
    return random.choice(templates)


def generate_mock_ai_summary(candidate: Candidate, category: str) -> str:
    """Build a deterministic mock summary from candidate profile data."""
    template = _pick_summary_template(candidate.id, category)
    return template.format(**_summary_context(candidate))


def _load_stored_summaries(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {"default": raw}


def _store_summary(candidate: Candidate, category: str, summary: str) -> None:
    summaries = _load_stored_summaries(candidate.ai_summary)
    summaries[category] = summary
    candidate.ai_summary = json.dumps(summaries)


# ── Candidates ────────────────────────────────────────────────────────────────

async def list_candidates(
    db: AsyncSession,
    status: Optional[str] = None,
    role_applied: Optional[str] = None,
    skill: Optional[str] = None,
    keyword: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
) -> dict:
    limit = min(limit, 50)
    query = select(Candidate).where(Candidate.deleted_at.is_(None))

    if status:
        query = query.where(Candidate.status == status)
    if role_applied:
        query = query.where(Candidate.role_applied.ilike(f"%{role_applied}%"))
    if skill:
        query = query.where(Candidate.skills.ilike(f'%"{skill}"%'))
    if keyword:
        query = query.where(
            or_(
                Candidate.name.ilike(f"%{keyword}%"),
                Candidate.email.ilike(f"%{keyword}%"),
                Candidate.role_applied.ilike(f"%{keyword}%"),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Candidate.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    candidates = result.scalars().all()

    items = []
    for c in candidates:
        items.append({
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "role_applied": c.role_applied,
            "status": c.status,
            "skills": _deserialize_skills(c.skills),
            "created_at": c.created_at,
        })

    return {
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < total,
    }


async def get_candidate(db: AsyncSession, candidate_id: str, current_user: User) -> dict:
    result = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.deleted_at.is_(None),
        )
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    scores_query = select(Score).where(Score.candidate_id == candidate_id)
    if current_user.role != "admin":
        scores_query = scores_query.where(Score.reviewer_id == current_user.id)
    scores_result = await db.execute(scores_query.order_by(Score.created_at.desc()))
    scores = scores_result.scalars().all()

    data = _candidate_to_dict(candidate)
    data["scores"] = [
        {
            "id": s.id,
            "candidate_id": s.candidate_id,
            "category": s.category,
            "score": s.score,
            "reviewer_id": s.reviewer_id,
            "note": s.note,
            "created_at": s.created_at,
        }
        for s in scores
    ]
    if current_user.role != "admin":
        data["internal_notes"] = None

    return data


async def create_candidate(db: AsyncSession, payload: CandidateCreate) -> dict:
    candidate = Candidate(
        name=payload.name,
        email=payload.email,
        role_applied=payload.role_applied,
        status="new",
        skills=_serialize_skills(payload.skills),
        internal_notes=payload.internal_notes,
    )
    db.add(candidate)
    await db.flush()
    await db.refresh(candidate)
    return _candidate_to_dict(candidate)


async def update_candidate(db: AsyncSession, candidate_id: str, payload: CandidateUpdate) -> dict:
    result = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.deleted_at.is_(None),
        )
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if payload.name is not None:
        candidate.name = payload.name
    if payload.role_applied is not None:
        candidate.role_applied = payload.role_applied
    if payload.status is not None:
        candidate.status = payload.status
    if payload.skills is not None:
        candidate.skills = _serialize_skills(payload.skills)
    if payload.internal_notes is not None:
        candidate.internal_notes = payload.internal_notes

    await db.flush()
    await db.refresh(candidate)
    return _candidate_to_dict(candidate)


async def soft_delete_candidate(db: AsyncSession, candidate_id: str) -> None:
    result = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.deleted_at.is_(None),
        )
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate.deleted_at = datetime.utcnow()
    candidate.status = "archived"
    await db.flush()


# ── Scores ────────────────────────────────────────────────────────────────────

async def submit_score(
    db: AsyncSession,
    candidate_id: str,
    payload: ScoreCreate,
    reviewer_id: str,
) -> dict:
    result = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.deleted_at.is_(None),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Candidate not found")

    score = Score(
        candidate_id=candidate_id,
        category=payload.category,
        score=payload.score,
        reviewer_id=reviewer_id,
        note=payload.note,
    )
    db.add(score)
    await db.flush()
    await db.refresh(score)
    return {
        "id": score.id,
        "candidate_id": score.candidate_id,
        "category": score.category,
        "score": score.score,
        "reviewer_id": score.reviewer_id,
        "note": score.note,
        "created_at": score.created_at,
    }


# ── AI Summary endpoint handler ───────────────────────────────────────────────

async def generate_summary(db: AsyncSession, candidate_id: str, category: str = "default") -> str:
    result = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.deleted_at.is_(None),
        )
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    await asyncio.sleep(2)  # simulate async LLM call
    summary = generate_mock_ai_summary(candidate, category)
    _store_summary(candidate, category, summary)
    await db.flush()

    return summary
