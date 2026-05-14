from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ApplicationStatus, JobApplication, JobPosting, Resume
from app.db.session import get_db
from app.schemas.applications import ApplicationCreate, ApplicationOut, ApplicationPatch
from app.services.jobs.normalize import normalize_url


router = APIRouter(prefix="/api/applications", tags=["applications"])


def _parse_status(raw: str | None) -> ApplicationStatus:
    if not raw:
        return ApplicationStatus.interested
    try:
        return ApplicationStatus(raw)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Use one of: {', '.join(s.value for s in ApplicationStatus)}",
        )


def _to_out(row: JobApplication) -> ApplicationOut:
    return ApplicationOut(
        id=row.id,
        job_posting_id=row.job_posting_id,
        resume_id=row.resume_id,
        title=row.title,
        company=row.company,
        location=row.location,
        source_url=row.source_url,
        normalized_url=row.normalized_url,
        status=row.status.value,
        applied_at=row.applied_at,
        next_follow_up_at=row.next_follow_up_at,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    db: Session = Depends(get_db),
    resume_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
) -> list[ApplicationOut]:
    q = db.query(JobApplication).order_by(JobApplication.updated_at.desc())
    if resume_id:
        q = q.filter(JobApplication.resume_id == resume_id)
    if status:
        st = _parse_status(status)
        q = q.filter(JobApplication.status == st)
    rows = q.limit(limit).all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(body: ApplicationCreate, db: Session = Depends(get_db)) -> ApplicationOut:
    normalized = normalize_url(body.source_url)
    if body.job_posting_id:
        jp = db.query(JobPosting).filter(JobPosting.id == body.job_posting_id).one_or_none()
        if not jp:
            raise HTTPException(status_code=404, detail="job_posting_id not found")
    if body.resume_id:
        if not db.query(Resume).filter(Resume.id == body.resume_id).one_or_none():
            raise HTTPException(status_code=404, detail="resume_id not found")

    row = JobApplication(
        job_posting_id=body.job_posting_id,
        resume_id=body.resume_id,
        title=body.title.strip(),
        company=body.company.strip(),
        location=body.location.strip() if body.location else None,
        source_url=body.source_url.strip(),
        normalized_url=normalized,
        status=_parse_status(body.status),
        applied_at=body.applied_at,
        next_follow_up_at=body.next_follow_up_at,
        notes=body.notes,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An application for this resume and posting URL already exists.",
        )
    db.refresh(row)
    return _to_out(row)


@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(application_id: UUID, db: Session = Depends(get_db)) -> ApplicationOut:
    row = db.query(JobApplication).filter(JobApplication.id == application_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    return _to_out(row)


@router.patch("/{application_id}", response_model=ApplicationOut)
def patch_application(
    application_id: UUID, body: ApplicationPatch, db: Session = Depends(get_db)
) -> ApplicationOut:
    row = db.query(JobApplication).filter(JobApplication.id == application_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")

    patch = body.model_dump(exclude_unset=True)
    if "title" in patch:
        row.title = patch["title"].strip()
    if "company" in patch:
        row.company = patch["company"].strip()
    if "location" in patch:
        row.location = (patch["location"] or "").strip() or None
    if "source_url" in patch:
        row.source_url = str(patch["source_url"]).strip()
        row.normalized_url = normalize_url(row.source_url)
    if "status" in patch:
        row.status = _parse_status(patch["status"])
    if "applied_at" in patch:
        row.applied_at = patch["applied_at"]
    if "next_follow_up_at" in patch:
        row.next_follow_up_at = patch["next_follow_up_at"]
    if "notes" in patch:
        row.notes = patch["notes"]

    row.updated_at = datetime.now(timezone.utc)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Update conflicts with existing application for same URL.")
    db.refresh(row)
    return _to_out(row)


@router.delete("/{application_id}", status_code=204, response_model=None)
def delete_application(application_id: UUID, db: Session = Depends(get_db)) -> None:
    row = db.query(JobApplication).filter(JobApplication.id == application_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(row)
    db.commit()
