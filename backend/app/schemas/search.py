from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


SearchMode = Literal["lexical", "semantic", "hybrid"]


class SearchRequest(BaseModel):
    query: str | None = None
    resume_id: UUID | None = None
    mode: SearchMode = "hybrid"
    k: int = Field(default=20, ge=1, le=50)
    location: str | None = None
    company: str | None = None
    recency_days: int | None = Field(default=None, ge=1, le=365)


class ScoreBreakdown(BaseModel):
    bm25: float
    semantic: float
    skill_overlap: float
    recency: float
    final: float


class MatchExplanation(BaseModel):
    matched_skills: list[str]
    missing_skills: list[str]
    top_bm25_terms: list[str]
    rationale: str


class SearchResult(BaseModel):
    job_id: UUID
    title: str
    company: str
    location: str | None = None
    description: str
    source_url: str
    normalized_url: str
    source: str | None = None
    date_posted: datetime | None = None
    crawled_at: datetime
    employment_type: str | None = None
    experience_level: str | None = None
    salary: str | None = None
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    category: str
    category_confidence: int | None = None
    score: ScoreBreakdown
    explanation: MatchExplanation


class SearchResponse(BaseModel):
    mode: SearchMode
    results: list[SearchResult]

