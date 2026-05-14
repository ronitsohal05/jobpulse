from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ApplicationCreate(BaseModel):
    job_posting_id: UUID | None = None
    resume_id: UUID | None = None
    title: str = Field(min_length=1, max_length=400)
    company: str = Field(min_length=1, max_length=400)
    location: str | None = Field(default=None, max_length=400)
    source_url: str = Field(min_length=1)
    status: str | None = Field(default="interested", description="interested|applied|screening|interview|offer|rejected|withdrawn")
    applied_at: datetime | None = None
    next_follow_up_at: datetime | None = None
    notes: str | None = None


class ApplicationPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=400)
    company: str | None = Field(default=None, min_length=1, max_length=400)
    location: str | None = Field(default=None, max_length=400)
    source_url: str | None = None
    status: str | None = None
    applied_at: datetime | None = None
    next_follow_up_at: datetime | None = None
    notes: str | None = None


class ApplicationOut(BaseModel):
    id: UUID
    job_posting_id: UUID | None
    resume_id: UUID | None
    title: str
    company: str
    location: str | None
    source_url: str
    normalized_url: str
    status: str
    applied_at: datetime | None
    next_follow_up_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
