from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Scores ────────────────────────────────────────────────────────────────────

class ScoreCreate(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    score: int = Field(ge=1, le=5)
    note: Optional[str] = None


class ScoreOut(BaseModel):
    id: str
    candidate_id: str
    category: str
    score: int
    reviewer_id: str
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Candidates ────────────────────────────────────────────────────────────────

class CandidateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    role_applied: str = Field(min_length=1, max_length=200)
    skills: List[str] = []
    internal_notes: Optional[str] = None


class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    role_applied: Optional[str] = None
    status: Optional[str] = None
    skills: Optional[List[str]] = None
    internal_notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed = {"new", "reviewed", "hired", "rejected", "archived"}
        if v and v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


class CandidateOut(BaseModel):
    id: str
    name: str
    email: str
    role_applied: str
    status: str
    skills: List[str]
    internal_notes: Optional[str]  # None for reviewers
    ai_summary: Optional[str]
    created_at: datetime
    scores: List[ScoreOut] = []

    class Config:
        from_attributes = True


class CandidateListItem(BaseModel):
    id: str
    name: str
    email: str
    role_applied: str
    status: str
    skills: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedCandidates(BaseModel):
    items: List[CandidateListItem]
    total: int
    offset: int
    limit: int
    has_more: bool
