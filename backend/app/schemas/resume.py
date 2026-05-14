from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ParsedResumeDataOut(BaseModel):
    id: UUID
    resume_id: UUID
    data: dict[str, Any]
    text_content: str
    experience_years: int | None = None
    created_at: datetime
    updated_at: datetime


class ResumeOut(BaseModel):
    id: UUID
    filename: str
    content_type: str
    created_at: datetime
    updated_at: datetime
    parsed: ParsedResumeDataOut | None = None


class ResumeUploadResponse(BaseModel):
    resume: ResumeOut
    queued: bool = Field(
        default=False,
        description="True if parsing/embedding was queued to worker instead of run inline.",
    )

