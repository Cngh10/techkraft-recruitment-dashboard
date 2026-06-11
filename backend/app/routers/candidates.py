import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..auth import get_current_user, require_admin
from ..models import User
from ..schemas import (
    CandidateCreate, CandidateUpdate, CandidateOut,
    PaginatedCandidates, ScoreCreate, ScoreOut
)
from ..services.candidate_service import (
    list_candidates, get_candidate, create_candidate,
    update_candidate, soft_delete_candidate, submit_score, generate_summary
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=PaginatedCandidates)
async def get_candidates(
    status: Optional[str] = Query(None, description="Filter by status: new/reviewed/hired/rejected"),
    role_applied: Optional[str] = Query(None, description="Filter by role (partial match)"),
    skill: Optional[str] = Query(None, description="Filter by skill"),
    keyword: Optional[str] = Query(None, description="Search name, email, role"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_candidates(db, status, role_applied, skill, keyword, offset, limit)


@router.post("", response_model=CandidateOut, status_code=201)
async def add_candidate(
    payload: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return await create_candidate(db, payload)


@router.get("/{candidate_id}", response_model=CandidateOut)
async def get_candidate_detail(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_candidate(db, candidate_id, current_user)


@router.patch("/{candidate_id}", response_model=CandidateOut)
async def patch_candidate(
    candidate_id: str,
    payload: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return await update_candidate(db, candidate_id, payload)


@router.delete("/{candidate_id}", status_code=204)
async def delete_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    await soft_delete_candidate(db, candidate_id)


@router.post("/{candidate_id}/scores", response_model=ScoreOut, status_code=201)
async def score_candidate(
    candidate_id: str,
    payload: ScoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await submit_score(db, candidate_id, payload, current_user.id)


@router.post("/{candidate_id}/summary")
async def trigger_summary(
    candidate_id: str,
    category: str = Query("default", description="Analysis category: Technical, Communication, Problem Solving, Culture Fit, Leadership"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a contextual AI summary for a specific evaluation category.
    Each category produces a unique, targeted analysis.
    """
    summary = await generate_summary(db, candidate_id, category)
    return {"summary": summary, "category": category}


@router.get("/{candidate_id}/summaries")
async def get_all_summaries(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all previously generated summaries for a candidate, keyed by category."""
    from sqlalchemy import select
    from ..models import Candidate

    result = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.deleted_at.is_(None),
        )
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    summaries = {}
    if candidate.ai_summary:
        try:
            summaries = json.loads(candidate.ai_summary)
        except Exception:
            summaries = {"default": candidate.ai_summary}

    return {"summaries": summaries}


@router.get("/{candidate_id}/stream")
async def stream_scores(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """SSE endpoint streaming score updates in real time."""
    from sqlalchemy import select
    from ..models import Score

    async def event_generator():
        last_count = 0
        for _ in range(60):
            await asyncio.sleep(1)
            query = select(Score).where(Score.candidate_id == candidate_id)
            if current_user.role != "admin":
                query = query.where(Score.reviewer_id == current_user.id)
            result = await db.execute(query)
            scores = result.scalars().all()
            if len(scores) != last_count:
                last_count = len(scores)
                data = [
                    {
                        "id": s.id,
                        "category": s.category,
                        "score": s.score,
                        "reviewer_id": s.reviewer_id,
                        "note": s.note,
                        "created_at": s.created_at.isoformat(),
                    }
                    for s in scores
                ]
                yield f"data: {json.dumps(data)}\n\n"
        yield 'data: {"done": true}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")
