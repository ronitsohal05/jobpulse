from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def _session() -> Session:
    return SessionLocal()


def parse_resume(resume_id: str) -> dict:
    resume_uuid = UUID(resume_id)
    db = _session()
    try:
        from app.services.resume_parser.pipeline import parse_and_persist_resume

        parsed = parse_and_persist_resume(db=db, resume_id=resume_uuid)
        db.commit()
        return {"resume_id": str(resume_uuid), "parsed_resume_data_id": str(parsed.id)}
    finally:
        db.close()


def embed_resume(resume_id: str) -> dict:
    resume_uuid = UUID(resume_id)
    db = _session()
    try:
        from app.services.embeddings.pipeline import embed_resume_by_id

        emb = embed_resume_by_id(db=db, resume_id=resume_uuid)
        db.commit()
        return {"resume_id": str(resume_uuid), "embedding_id": str(emb.id)}
    finally:
        db.close()


def embed_job(job_id: str) -> dict:
    job_uuid = UUID(job_id)
    db = _session()
    try:
        from app.services.embeddings.pipeline import embed_job_by_id

        emb = embed_job_by_id(db=db, job_id=job_uuid)
        db.commit()
        return {"job_id": str(job_uuid), "embedding_id": str(emb.id)}
    finally:
        db.close()


def crawl_source(source_id: str) -> dict:
    source_uuid = UUID(source_id)
    db = _session()
    try:
        from app.services.crawler.pipeline import crawl_and_ingest_source

        result = crawl_and_ingest_source(db=db, source_id=source_uuid)
        db.commit()
        return result
    finally:
        db.close()


def update_topics() -> dict:
    db = _session()
    try:
        from app.services.topics.pipeline import recompute_topics

        result = recompute_topics(db=db)
        db.commit()
        return result
    finally:
        db.close()


def update_events() -> dict:
    db = _session()
    try:
        from app.services.events.pipeline import recompute_events

        result = recompute_events(db=db)
        db.commit()
        return result
    finally:
        db.close()

