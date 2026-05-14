from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import ParsedResumeData, Resume, ResumeSkill, Skill
from app.services.resume_parser.extract_text import extract_text_from_docx, extract_text_from_pdf
from app.services.resume_parser.parse import parse_resume_text
from app.services.skills.taxonomy import normalize_skill


def _upsert_skill(db: Session, canonical: str) -> Skill:
    canonical = normalize_skill(canonical)
    existing = db.query(Skill).filter(Skill.canonical == canonical).one_or_none()
    if existing:
        return existing
    s = Skill(canonical=canonical)
    db.add(s)
    db.flush()
    return s


def parse_and_persist_resume(db: Session, resume_id: UUID) -> ParsedResumeData:
    resume = db.query(Resume).filter(Resume.id == resume_id).one()

    if resume.content_type in ("application/pdf", "application/x-pdf") or resume.filename.lower().endswith(
        ".pdf"
    ):
        text = extract_text_from_pdf(resume.file_bytes)
    elif resume.content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ) or resume.filename.lower().endswith((".docx", ".doc")):
        text = extract_text_from_docx(resume.file_bytes)
    else:
        text = ""

    parsed_json = parse_resume_text(text)
    experience_years = parsed_json.get("experience_years")

    existing = db.query(ParsedResumeData).filter(ParsedResumeData.resume_id == resume_id).one_or_none()
    if existing:
        existing.data = parsed_json
        existing.text_content = text
        existing.experience_years = experience_years
        parsed = existing
    else:
        parsed = ParsedResumeData(
            resume_id=resume_id,
            data=parsed_json,
            text_content=text,
            experience_years=experience_years,
        )
        db.add(parsed)
        db.flush()

    # Replace resume skills
    db.query(ResumeSkill).filter(ResumeSkill.resume_id == resume_id).delete()
    for skill in parsed_json.get("skills", []):
        sk = _upsert_skill(db, skill)
        db.add(ResumeSkill(resume_id=resume_id, skill_id=sk.id, weight=1))

    return parsed

