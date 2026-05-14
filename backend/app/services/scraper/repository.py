from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import JobPosting, JobSkill, Skill
from app.schemas.jobs import JobIn
from app.services.embeddings.pipeline import embed_job_by_id
from app.services.jobs.normalize import normalize_url
from app.services.skills.taxonomy import normalize_skill


class JobRepository:
    """Persistence layer for scraped JobIn rows (mirrors /api/jobs/ingest semantics)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _upsert_skill(self, canonical: str) -> Skill:
        canonical = normalize_skill(canonical)
        existing = self.db.query(Skill).filter(Skill.canonical == canonical).one_or_none()
        if existing:
            return existing
        s = Skill(canonical=canonical)
        self.db.add(s)
        self.db.flush()
        return s

    def upsert_job(self, job: JobIn, *, embed: bool = True) -> tuple[JobPosting, bool]:
        """
        Insert if new (by normalized URL or job_hash). Returns (row, created_bool).
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        normalized = normalize_url(job.source_url)
        job_hash = JobPosting.compute_job_hash(job.company, job.title, job.location, job.description)

        existing = (
            self.db.query(JobPosting)
            .filter((JobPosting.normalized_url == normalized) | (JobPosting.job_hash == job_hash))
            .one_or_none()
        )
        if existing:
            return existing, False

        jp = JobPosting(
            source=job.source,
            source_url=job.source_url,
            normalized_url=normalized,
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description,
            required_skills_raw=job.required_skills,
            preferred_skills_raw=job.preferred_skills,
            employment_type=job.employment_type,
            experience_level=job.experience_level,
            salary=job.salary,
            date_posted=job.date_posted,
            crawled_at=now,
            job_hash=job_hash,
            raw_html=None,
        )
        self.db.add(jp)
        try:
            with self.db.begin_nested():
                self.db.flush()
        except IntegrityError:
            self.db.expunge(jp)
            existing = (
                self.db.query(JobPosting)
                .filter(JobPosting.normalized_url == normalized)
                .one_or_none()
            )
            if existing:
                return existing, False
            raise

        self.db.query(JobSkill).filter(JobSkill.job_id == jp.id).delete()
        for s in job.required_skills or []:
            sk = self._upsert_skill(s)
            self.db.add(JobSkill(job_id=jp.id, skill_id=sk.id, kind="required"))
        for s in job.preferred_skills or []:
            sk = self._upsert_skill(s)
            self.db.add(JobSkill(job_id=jp.id, skill_id=sk.id, kind="preferred"))

        if embed:
            embed_job_by_id(db=self.db, job_id=jp.id)

        return jp, True

    def upsert_many(
        self, jobs: list[JobIn], *, embed: bool = True
    ) -> dict[str, int | list[JobPosting]]:
        created_rows: list[JobPosting] = []
        created = 0
        duplicates = 0
        for job in jobs:
            row, was_created = self.upsert_job(job, embed=embed)
            if was_created:
                created += 1
                created_rows.append(row)
            else:
                duplicates += 1
        return {"created": created, "duplicates_skipped": duplicates, "jobs": created_rows}
