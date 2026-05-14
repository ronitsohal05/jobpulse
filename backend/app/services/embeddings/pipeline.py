from __future__ import annotations

from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session

from app.db.models import Embedding, EmbeddingEntityType, JobPosting, ParsedResumeData, Resume
from app.services.embeddings.model import get_model
from app.services.vector.faiss_index import FaissIndex
from app.settings import settings


def _upsert_embedding(
    db: Session,
    *,
    entity_type: EmbeddingEntityType,
    entity_id: UUID,
    model: str,
    dims: int,
    faiss_id: int,
) -> Embedding:
    existing = (
        db.query(Embedding)
        .filter(
            Embedding.entity_type == entity_type,
            Embedding.entity_id == entity_id,
            Embedding.model == model,
        )
        .one_or_none()
    )
    if existing:
        existing.dims = dims
        existing.faiss_id = faiss_id
        return existing
    e = Embedding(
        entity_type=entity_type,
        entity_id=entity_id,
        model=model,
        dims=dims,
        faiss_id=faiss_id,
    )
    db.add(e)
    db.flush()
    return e


def embed_job_by_id(db: Session, job_id: UUID) -> Embedding:
    job = db.query(JobPosting).filter(JobPosting.id == job_id).one()
    text = f"{job.title}\n{job.company}\n{job.location or ''}\n\n{job.description}"

    model_name = settings.embeddings_model
    model = get_model()
    vec = np.asarray(model.encode([text], normalize_embeddings=False))
    dims = int(vec.shape[1])

    index = FaissIndex(kind="jobs", dims=dims, model=model_name)
    faiss_ids = index.add(vec)
    emb = _upsert_embedding(
        db,
        entity_type=EmbeddingEntityType.job,
        entity_id=job.id,
        model=model_name,
        dims=dims,
        faiss_id=faiss_ids[0],
    )
    return emb


def embed_resume_by_id(db: Session, resume_id: UUID) -> Embedding:
    resume = db.query(Resume).filter(Resume.id == resume_id).one()
    parsed = db.query(ParsedResumeData).filter(ParsedResumeData.resume_id == resume.id).one_or_none()
    text = parsed.text_content if parsed else ""
    if not text:
        text = resume.filename

    model_name = settings.embeddings_model
    model = get_model()
    vec = np.asarray(model.encode([text], normalize_embeddings=False))
    dims = int(vec.shape[1])

    index = FaissIndex(kind="resumes", dims=dims, model=model_name)
    faiss_ids = index.add(vec)
    emb = _upsert_embedding(
        db,
        entity_type=EmbeddingEntityType.resume,
        entity_id=resume.id,
        model=model_name,
        dims=dims,
        faiss_id=faiss_ids[0],
    )
    return emb

