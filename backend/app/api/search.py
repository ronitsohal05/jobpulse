from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.retrieval.search import search_jobs


router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(req: SearchRequest, db: Session = Depends(get_db)) -> SearchResponse:
    if not req.query and not req.resume_id:
        raise HTTPException(status_code=400, detail="Provide query or resume_id")

    query = req.query or ""
    results = search_jobs(
        db,
        query=query,
        k=req.k,
        mode=req.mode,
        resume_id=req.resume_id,
        location=req.location,
        company=req.company,
        recency_days=req.recency_days,
    )

    out_results: list[SearchResult] = []
    for r in results:
        j = r["job"]
        out_results.append(
            SearchResult(
                job_id=j.id,
                title=j.title,
                company=j.company,
                location=j.location,
                description=j.description,
                source_url=j.source_url,
                normalized_url=j.normalized_url,
                source=j.source,
                date_posted=j.date_posted,
                crawled_at=j.crawled_at,
                employment_type=j.employment_type,
                experience_level=j.experience_level,
                salary=j.salary,
                required_skills=j.required_skills_raw,
                preferred_skills=j.preferred_skills_raw,
                category=j.category.value,
                category_confidence=j.category_confidence,
                score=r["score"],
                explanation=r["explanation"],
            )
        )

    return SearchResponse(mode=req.mode, results=out_results)

