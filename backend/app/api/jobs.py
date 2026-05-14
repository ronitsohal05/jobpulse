from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import JobPosting, JobSkill, Skill
from app.db.session import get_db
from app.schemas.jobs import JobIngestRequest, JobIngestResponse, JobOut
from app.services.embeddings.pipeline import embed_job_by_id
from app.services.jobs.normalize import normalize_url
from app.services.skills.taxonomy import normalize_skill


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _upsert_skill(db: Session, canonical: str) -> Skill:
    canonical = normalize_skill(canonical)
    existing = db.query(Skill).filter(Skill.canonical == canonical).one_or_none()
    if existing:
        return existing
    s = Skill(canonical=canonical)
    db.add(s)
    db.flush()
    return s


def _to_job_out(j: JobPosting) -> JobOut:
    return JobOut(
        id=j.id,
        title=j.title,
        company=j.company,
        location=j.location,
        description=j.description,
        source_url=j.source_url,
        normalized_url=j.normalized_url,
        source=j.source,
        date_posted=j.date_posted,
        crawled_at=j.crawled_at,
        job_hash=j.job_hash,
        category=j.category.value,
        category_confidence=j.category_confidence,
    )


@router.post("/ingest", response_model=JobIngestResponse)
def ingest_jobs(req: JobIngestRequest, db: Session = Depends(get_db)) -> JobIngestResponse:
    created = 0
    duplicates = 0
    embedded = 0
    out: list[JobOut] = []

    now = datetime.now(timezone.utc)

    for job in req.jobs:
        normalized = normalize_url(job.source_url)
        job_hash = JobPosting.compute_job_hash(job.company, job.title, job.location, job.description)

        existing = (
            db.query(JobPosting)
            .filter((JobPosting.normalized_url == normalized) | (JobPosting.job_hash == job_hash))
            .one_or_none()
        )
        if existing:
            duplicates += 1
            out.append(_to_job_out(existing))
            continue

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
        db.add(jp)
        db.flush()

        # Store skills (best-effort): canonicalize and create mapping rows
        db.query(JobSkill).filter(JobSkill.job_id == jp.id).delete()
        for s in (job.required_skills or []):
            sk = _upsert_skill(db, s)
            db.add(JobSkill(job_id=jp.id, skill_id=sk.id, kind="required"))
        for s in (job.preferred_skills or []):
            sk = _upsert_skill(db, s)
            db.add(JobSkill(job_id=jp.id, skill_id=sk.id, kind="preferred"))

        created += 1

        if req.embed:
            embed_job_by_id(db=db, job_id=jp.id)
            embedded += 1

        out.append(_to_job_out(jp))

    db.commit()
    return JobIngestResponse(
        created=created,
        duplicates_skipped=duplicates,
        embedded=embedded,
        jobs=out,
    )


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db), limit: int = 50, offset: int = 0) -> list[JobOut]:
    jobs = (
        db.query(JobPosting)
        .order_by(JobPosting.crawled_at.desc())
        .limit(min(limit, 200))
        .offset(max(offset, 0))
        .all()
    )
    return [_to_job_out(j) for j in jobs]


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: UUID, db: Session = Depends(get_db)) -> JobOut:
    job = db.query(JobPosting).filter(JobPosting.id == job_id).one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_job_out(job)

