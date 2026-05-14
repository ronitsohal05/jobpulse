from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.models import ParsedResumeData, Resume
from app.db.session import get_db
from app.schemas.resume import ParsedResumeDataOut, ResumeOut, ResumeUploadResponse
from app.services.resume_parser.pipeline import parse_and_persist_resume


router = APIRouter(prefix="/api/resume", tags=["resume"])


def _to_parsed_out(p: ParsedResumeData) -> ParsedResumeDataOut:
    return ParsedResumeDataOut(
        id=p.id,
        resume_id=p.resume_id,
        data=p.data,
        text_content=p.text_content,
        experience_years=p.experience_years,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _to_resume_out(r: Resume, parsed: ParsedResumeData | None) -> ResumeOut:
    return ResumeOut(
        id=r.id,
        filename=r.filename,
        content_type=r.content_type,
        created_at=r.created_at,
        updated_at=r.updated_at,
        parsed=_to_parsed_out(parsed) if parsed else None,
    )


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ResumeUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    resume = Resume(
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        file_bytes=file_bytes,
    )
    db.add(resume)
    db.flush()

    parsed = parse_and_persist_resume(db=db, resume_id=resume.id)
    db.commit()

    return ResumeUploadResponse(resume=_to_resume_out(resume, parsed), queued=False)


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: UUID, db: Session = Depends(get_db)) -> ResumeOut:
    resume = db.query(Resume).filter(Resume.id == resume_id).one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    parsed = db.query(ParsedResumeData).filter(ParsedResumeData.resume_id == resume.id).one_or_none()
    return _to_resume_out(resume, parsed)

