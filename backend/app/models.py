from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


def gen_id():
    return str(uuid.uuid4())


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    role_applied = Column(String, nullable=False)
    status = Column(String, nullable=False, default="new")  # new/reviewed/hired/rejected/archived
    skills = Column(Text, nullable=False, default="[]")     # JSON array stored as text
    internal_notes = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_candidates_status", "status"),
        Index("idx_candidates_role_applied", "role_applied"),
    )


class Score(Base):
    __tablename__ = "scores"

    id = Column(String, primary_key=True, default=gen_id)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    category = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    reviewer_id = Column(String, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_scores_candidate_id", "candidate_id"),
        Index("idx_scores_reviewer_id", "reviewer_id"),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="reviewer")  # reviewer | admin
    created_at = Column(DateTime, default=datetime.utcnow)
