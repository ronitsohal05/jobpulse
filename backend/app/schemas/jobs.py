from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class JobIn(BaseModel):
    title: str
    company: str
    location: str | None = None
    description: str
    source_url: str
    source: str | None = None
    date_posted: datetime | None = None
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    employment_type: str | None = None
    experience_level: str | None = None
    salary: str | None = None


class JobIngestRequest(BaseModel):
    jobs: list[JobIn] = Field(min_length=1)
    embed: bool = True


class JobOut(BaseModel):
    id: UUID
    title: str
    company: str
    location: str | None
    description: str
    source_url: str
    normalized_url: str
    source: str | None
    date_posted: datetime | None
    crawled_at: datetime
    job_hash: str
    category: str
    category_confidence: int | None


class JobIngestResponse(BaseModel):
    created: int
    duplicates_skipped: int
    embedded: int
    jobs: list[JobOut]

