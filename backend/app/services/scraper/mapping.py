from __future__ import annotations

from app.schemas.jobs import JobIn
from app.services.crawler.extract import ExtractedJob

from .normalizer import normalize_date_posted


def job_in_from_extracted(ex: ExtractedJob, source_url: str, source: str) -> JobIn:
    return JobIn(
        title=ex.title,
        company=ex.company,
        location=ex.location,
        description=ex.description or ex.title,
        source_url=source_url,
        source=source,
        date_posted=normalize_date_posted(ex.date_posted),
        required_skills=ex.required_skills,
        preferred_skills=ex.preferred_skills,
        employment_type=ex.employment_type,
        experience_level=None,
        salary=ex.salary,
    )
