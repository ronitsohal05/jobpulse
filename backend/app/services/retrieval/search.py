from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import UUID

import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.db.models import Embedding, EmbeddingEntityType, JobPosting, JobSkill, ResumeSkill, Skill
from app.services.embeddings.model import get_model
from app.services.vector.faiss_index import FaissIndex
from app.settings import settings


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[^A-Za-z0-9\+\#\.]+", text.lower()) if t]


def _minmax_norm(scores: dict[UUID, float]) -> dict[UUID, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if math.isclose(lo, hi):
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def _recency_score(crawled_at: datetime, now: datetime, horizon_days: int = 60) -> float:
    age_days = max((now - crawled_at).total_seconds() / 86400.0, 0.0)
    return max(0.0, 1.0 - (age_days / float(horizon_days)))


def _get_resume_skills(db: Session, resume_id: UUID) -> set[str]:
    rows = (
        db.query(Skill.canonical)
        .join(ResumeSkill, ResumeSkill.skill_id == Skill.id)
        .filter(ResumeSkill.resume_id == resume_id)
        .all()
    )
    return {r[0] for r in rows}


def _get_job_skills(db: Session, job_id: UUID) -> set[str]:
    rows = (
        db.query(Skill.canonical)
        .join(JobSkill, JobSkill.skill_id == Skill.id)
        .filter(JobSkill.job_id == job_id)
        .all()
    )
    return {r[0] for r in rows}


def _top_terms(query: str) -> list[str]:
    toks = _tokenize(query)
    return [t for t, _ in Counter(toks).most_common(5)]


def search_jobs(
    db: Session,
    *,
    query: str,
    k: int,
    mode: str,
    resume_id: UUID | None = None,
    location: str | None = None,
    company: str | None = None,
    recency_days: int | None = None,
) -> list[dict]:
    q = db.query(JobPosting)
    if location:
        q = q.filter(JobPosting.location.ilike(f"%{location}%"))
    if company:
        q = q.filter(JobPosting.company.ilike(f"%{company}%"))
    if recency_days:
        cutoff = datetime.now(timezone.utc)
        q = q.filter(JobPosting.crawled_at >= (cutoff - timedelta(days=recency_days)))
    jobs: list[JobPosting] = q.limit(5000).all()

    if not jobs:
        return []

    now = datetime.now(timezone.utc)
    query_text = query.strip()

    # Lexical BM25
    docs = [f"{j.title}\n{j.company}\n{j.location or ''}\n\n{j.description}" for j in jobs]
    tokenized = [_tokenize(d) for d in docs]
    bm25 = BM25Okapi(tokenized)
    bm25_scores_arr = bm25.get_scores(_tokenize(query_text))
    bm25_scores: dict[UUID, float] = {jobs[i].id: float(bm25_scores_arr[i]) for i in range(len(jobs))}
    bm25_norm = _minmax_norm(bm25_scores)

    # Semantic
    semantic_norm: dict[UUID, float] = {j.id: 0.0 for j in jobs}
    if mode in ("semantic", "hybrid"):
        model = get_model()
        qvec = np.asarray(model.encode([query_text], normalize_embeddings=False))
        dims = int(qvec.shape[1])
        index = FaissIndex(kind="jobs", dims=dims, model=settings.embeddings_model)
        scores, ids = index.search(qvec, k=min(max(k * 5, 50), 200))
        faiss_ids = [int(i) for i in ids[0] if i >= 0]
        if faiss_ids:
            rows = (
                db.query(Embedding.entity_id, Embedding.faiss_id)
                .filter(
                    Embedding.entity_type == EmbeddingEntityType.job,
                    Embedding.model == settings.embeddings_model,
                    Embedding.faiss_id.in_(faiss_ids),
                )
                .all()
            )
            faiss_to_job = {int(faiss_id): entity_id for entity_id, faiss_id in rows}
            sem_scores: dict[UUID, float] = {}
            for score, fid in zip(scores[0].tolist(), ids[0].tolist(), strict=False):
                if fid < 0:
                    continue
                jid = faiss_to_job.get(int(fid))
                if jid:
                    sem_scores[jid] = float(score)
            semantic_norm = _minmax_norm(sem_scores)

    resume_skills = _get_resume_skills(db, resume_id) if resume_id else set()

    results: list[dict] = []
    for j in jobs:
        bm25_s = bm25_norm.get(j.id, 0.0)
        sem_s = semantic_norm.get(j.id, 0.0)
        rec_s = _recency_score(j.crawled_at, now)

        job_skills = _get_job_skills(db, j.id) if resume_skills else set()
        if resume_skills:
            matched = sorted(resume_skills.intersection(job_skills))
            missing = sorted(job_skills.difference(resume_skills))
            overlap = len(matched) / max(len(job_skills), 1)
        else:
            matched = []
            missing = []
            overlap = 0.0

        if mode == "lexical":
            final = bm25_s
        elif mode == "semantic":
            final = sem_s
        else:
            final = 0.35 * bm25_s + 0.35 * sem_s + 0.20 * overlap + 0.10 * rec_s

        results.append(
            {
                "job": j,
                "score": {
                    "bm25": bm25_s,
                    "semantic": sem_s,
                    "skill_overlap": overlap,
                    "recency": rec_s,
                    "final": final,
                },
                "explanation": {
                    "matched_skills": matched,
                    "missing_skills": missing,
                    "top_bm25_terms": _top_terms(query_text),
                    "rationale": "Hybrid match combining keyword relevance, semantic similarity, skill overlap, and recency.",
                },
            }
        )

    results.sort(key=lambda r: r["score"]["final"], reverse=True)
    return results[:k]

